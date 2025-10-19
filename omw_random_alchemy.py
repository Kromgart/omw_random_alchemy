import re, sys, random, os, subprocess
import argparse


#---------------------------------------------------------
#                       Args
#---------------------------------------------------------

parser = argparse.ArgumentParser()

parser.add_argument(
    "--min-effects", choices=[1, 2, 3], type=int, default=1,
    help="Ensure that every ingredient has at least this amount of effects (or fail, if that is not possible)"
)

parser.add_argument(
    "--keep-yaml", default=False, action="store_true",
    help="The intermediate *.yaml file with new data will not be deleted, and could be investigated (for science or spoilers)"
)

parser.add_argument(
    "--ignore-food", default=False, action="store_true",
    help="Ingridients that have only one effect 'RestoreFatigue' will be excluded from the process"
)

parser.add_argument(
    "--no-loners", default=False, action="store_true",
    help="For each effect that is assigned to only one ingredient an additional effect instance"
         "will be added to the pool of effects. This should make it theoretically possible to brew"
         "a potion with such effect (if you get both ingredients)"
)

parser.add_argument(
    "--print-clones", default=False, action="store_true",
    help="Print record ids of ingredients which were determined to be clones "
         "(usually this happens because of existence of 'cursed' versions of items). "
         "Cloned items of the same type will have the same effects"
)

parser.add_argument(
    "-i", "--input-yaml", help="Directly give input yaml data. This will skip getting initial data by delta_plugin"
)

parser.add_argument(
    "-o", "--output-dir", default="./",
    help="Path of the directory where the intermediate and the final output file will be generated"
)

cmd_args = parser.parse_args()

random_mode = "shuffle"
keep_yaml = cmd_args.keep_yaml
min_effects = cmd_args.min_effects
ignore_food = cmd_args.ignore_food
no_loners = cmd_args.no_loners
print_clones = cmd_args.print_clones
yaml_in_custom = cmd_args.input_yaml
output_dir = cmd_args.output_dir


#---------------------------------------------------------
#                       Helpers
#---------------------------------------------------------


class Effect:
    rx_parse = re.compile(r'\n\s+- effect:\s+(?P<type>\w+)(?:\n\s+attribute:\s+(?P<attribute>\w+))?(?:\n\s+skill:\s+(?P<skill>\w+))?', re.DOTALL)

    def __init__(self, name, attribute, skill):
        self.name = sys.intern(name)
        self.attribute = sys.intern(attribute)
        self.skill = sys.intern(skill)

    def __format__(self, fmt):
        return f"  - {self.name} {self.attribute} {self.skill}"

    def __hash__(self):
        return hash((self.name, self.attribute, self.skill))

    def __eq__(self, other):
        return self.name == other.name and self.attribute == other.attribute and self.skill == other.skill

    def write_to(self, file, indent):
        file.write(f"{indent}- effect: {self.name}\n")
        if self.attribute:
            file.write(f"{indent}  attribute: {self.attribute}\n")
        if self.skill:
            file.write(f"{indent}  skill: {self.skill}\n")

    def is_compatible_with(self, other_effects):
        for e in other_effects:
            if self == e:
                # prevent duplicate effects
                return False
        return True
        

class Ingredient:
    rx_header_name = re.compile(r'\n\s+name:\s+(.+?[^\s])\s*?\n', re.DOTALL)
    rx_header_model = re.compile(r'\n\s+model:\s+(.+?[^\s])\s*?\n', re.DOTALL)
    rx_header_icon = re.compile(r'\n\s+icon:\s+(.+?[^\s])\s*?\n', re.DOTALL)
    rx_header_weight = re.compile(r'\n\s+weight:\s+([^\s]+)\s*?\n', re.DOTALL)
    rx_header_value = re.compile(r'\n\s+value:\s+([^\s]+)\s*?\n', re.DOTALL)

    def __init__(self, record_id, header, indent, str_effects, tail):
        self.record_id = record_id
        self.header = header
        self.tail = tail
        self.indent = sys.intern(indent + "  ")
        self.effects = []

        for (eff, attr, skill) in Effect.rx_parse.findall(str_effects):
            self.effects.append(Effect(eff, attr, skill))

        name = self.rx_header_name.search(self.header)
        if not name:
            print(f"Warning: ingredient {self.record_id} doesn't have a name")
        else:
            name = name.group(1)

        model = self.rx_header_model.search(self.header)
        if not model:
            print(f"Warning: ingredient {self.record_id} doesn't have a model")
        else:
            model = model.group(1)

        icon = self.rx_header_icon.search(self.header)
        if not icon:
            print(f"Warning: ingredient {self.record_id} doesn't have an icon")
        else:
            icon = icon.group(1)
            
        weight = self.rx_header_weight.search(self.header)
        if not weight:
            print(f"Warning: ingredient {self.record_id} doesn't have a weight")
        else:
            weight = weight.group(1)

        value = self.rx_header_value.search(self.header)
        if not value:
            print(f"Warning: ingredient {self.record_id} doesn't have a value")
        else:
            value = value.group(1)

        # print(f"{name} {model} {icon} {weight} {value}")
        self.uniqueness_key = hash((name, model, icon, weight, value))

    def __format__(self, fmt):
        b = [self.record_id]
        b.extend(f"{e}" for e in self.effects)
        return "\n".join(b)

    def from_yaml(yaml_string, ignore_food):
        good, skip, clones = [], [], {}
        rx_iter_ingredients = re.finditer(
            r'\n(?P<header>\s+"Ingredient::(?P<record_id>[^"]+)":\s*\n.+?\n(?P<indent>\s+)effects:\s*)'
            r'(?P<effects>\[\]|\n.+?)'
            r'(\n(?P<tail>(?P=indent)\w.+?))?(?=$|\n\s+"Ingredient::)',
            yaml_string, re.DOTALL)
        for i in rx_iter_ingredients:
            x = Ingredient(i.group("record_id"), i.group("header"), i.group("indent"), i.group("effects"), i.group("tail"))
            if not x.effects:
                # let's not touch these ingredient-without-effects, leave them as they are
                skip.append(x)
            elif ignore_food and len(x.effects) == 1 and x.effects[0].name == "RestoreFatigue":
                skip.append(x)
            elif x.uniqueness_key in clones:
                # this is non-first clone
                clones[x.uniqueness_key].append(x)
                if print_clones:
                    print(f"Clone detected: {x.record_id}")
            else:
                clones[x.uniqueness_key] = []
                good.append(x)

        return (good, clones, skip)


def remove_at(lst, idx):
    if idx == len(lst) - 1:
        return lst.pop()
    else:
        out = lst[idx]
        lst[idx] = lst.pop()
        return out

def remove_random(lst):
    idx = random.randrange(len(lst))
    return remove_at(lst, idx)

def strip_effects_into_jar(ingredients, no_loners):
    aggregator = {}
    collected = 0
    max_freq = 0
    for i in ingredients:
        for e in i.effects:
            this_freq = aggregator.get(e, 0) + 1
            aggregator[e] = this_freq
            max_freq = max(max_freq, this_freq)
            collected += 1

        i.effects.clear()
       
    jar = [ [] for i in range(max_freq + 1)]

    for (ef, count) in aggregator.items():
        jar[count].append(ef)


    if no_loners and jar[1]:
        print(f"Adding {len(jar[1])} effects to the effects pool due to --no-loners argument")
        jar[2].extend(jar[1])
        jar[1].clear()
    
    print(f"Collected {collected} existing effects. The most frequent effect ({jar[-1][0].name}) is used {max_freq} times")
    return jar


total_effects_added = 0
def move_random_effect(ingredient, jar):
    global total_effects_added
    
    biggest_bucket_idx = len(jar) - 1
    # trying the most frequent effects first
    for current_bucket_idx in reversed(range(len(jar))):
        # print(f"Trying bucket {current_bucket_idx}")
        current_bucket = jar[current_bucket_idx]
        if not current_bucket:
            if current_bucket_idx == biggest_bucket_idx:
                # The biggest bucket is empty, no need to keep it around
                biggest_bucket_idx -= 1
                jar.pop()
            continue

        current_failed_picks = []

        while current_bucket:
            new_effect = remove_random(current_bucket)
            
            if not new_effect.is_compatible_with(ingredient.effects):
                current_failed_picks.append(new_effect)
            else:
                # Success!
                ingredient.effects.append(new_effect)
                total_effects_added += 1
                # Bring back the incompatible ones (if there are any)
                current_bucket.extend(current_failed_picks)

                if not current_bucket and current_bucket_idx == biggest_bucket_idx:
                    # the biggest bucket have just got exhausted, don't keep it
                    jar.pop()

                # Move the effect to the N-1 frequency bucket
                # Currently this never moves the applied effect to the final 'zero' bucket.
                # (if the effect was in bucket '1', it is just removed from the jar for good)
                # This could probably be changed to 'reuse' instances of already applied effects
                # when all 'original' effects in the jar have been used up
                if current_bucket_idx >= 2:
                    jar[current_bucket_idx - 1].append(new_effect)

                # Delete the final 'zero' bucket (see above)
                if len(jar) == 1 and not jar[0]:
                    jar.pop()

                return True

        # end while
        # Nothing found in this bucket. Don't lose the failed picks before going down
        jar[current_bucket_idx] = current_failed_picks
        
    # end for
    return False


def finish_ingredient(i, clones, output):
    output_ingredients.append(i)
    for clone in clones.pop(i.uniqueness_key):
        clone.effects = i.effects
        output.append(clone)


#---------------------------------------------------------
#                 Process input data
#---------------------------------------------------------


if yaml_in_custom:
    yaml_in_path = yaml_in_custom
else:
    plugin_in_path = os.path.join(output_dir, "tmp_source_alchemy.omwaddon")
    print(f"Generating plugin with all ingredients...")
    run_result = subprocess.run(["./delta_plugin", "filter", "--all", "-o", f"{plugin_in_path}", "match", "Ingredient"])
    if run_result.returncode != 0:
        sys.exit("delta_plugin returned error. Aborting...")

    yaml_in_path = os.path.join(output_dir, "tmp_source_alchemy.yaml")
    print(f"Converting plugin with to yaml...")
    run_result = subprocess.run(["./delta_plugin", "convert", "-o", f"{output_dir}", f"{plugin_in_path}"])
    if run_result.returncode != 0:
        sys.exit("delta_plugin returned error. Aborting...")

yaml_in = open(yaml_in_path).read()

file_header = re.search(r'^.+\nrecords:', yaml_in, re.DOTALL)
if not file_header:
   print("Cannot parse the plugin's header from the input. Aborting...") 

# simple regex that should definitely catch all ingredients, used for double checks
ingredients_all = re.findall(r'\n\s+"Ingredient::([^"]+)":', yaml_in, re.DOTALL)

(tmp_ingredients, ingredient_clones, output_ingredients) = Ingredient.from_yaml(yaml_in, ignore_food)
clones_count = sum(len(xs) for xs in ingredient_clones.values())
print(f"{len(tmp_ingredients)} ingredients (with {clones_count} clones) will be updated, {len(output_ingredients)} will be kept intact")
 
# to ensure we didn't miss someone with the big regex
assert len(ingredients_all) == (len(tmp_ingredients) + clones_count + len(output_ingredients))

#---------------------------------------------------------
#            Prepare and distribute effects
#---------------------------------------------------------

jar = None

if random_mode == "shuffle":
    jar = strip_effects_into_jar(tmp_ingredients, no_loners)

assert jar
print(f"Assigning at least {min_effects} effect(s) to each ingredient, starting from most frequent ones...")
# print(f"Total effects added: {total_effects_added}, len(jar): {len(jar)}")

for k in range(min_effects):
    effect_added = []
    
    while tmp_ingredients:
        i = remove_random(tmp_ingredients)
        move_random_effect(i, jar)
        effect_added.append(i)

    tmp_ingredients = effect_added

print(f"Applied {total_effects_added} effects evenly onto {len(tmp_ingredients)} ingredients")
assert total_effects_added == len(tmp_ingredients) * min_effects
print("Redistributing remaining effects...")
# print(f"Total effects added: {total_effects_added}, len(jar): {len(jar)}")

while jar:
    if not tmp_ingredients:
        remains = sum(len(b) for b in jar)
        print(f"Error: there are no more available ingredients, but still {remains} effects in {len(jar)} buckets of the jar:")
        for (b_idx, b) in enumerate(jar):
            for e in b:
                print(f"{b_idx}: {e}")
        sys.exit("Aborting...")

    idx = random.randrange(len(tmp_ingredients))
    ingredient = tmp_ingredients[idx]

    if not move_random_effect(ingredient, jar) or len(ingredient.effects) == 4:
        # Either the ingredient has 4 effects, or there
        # are no valid effect left in the jar for it
        finish_ingredient(ingredient, ingredient_clones, output_ingredients)
        remove_at(tmp_ingredients, idx)

for i in tmp_ingredients:
    finish_ingredient(i, ingredient_clones, output_ingredients)

assert not ingredient_clones
tmp_ingredients.clear()

# Did we lose something?
# print(f"{len(ingredients_all)} == {len(output_ingredients)}")
assert len(ingredients_all) == len(output_ingredients)

#---------------------------------------------------------
#               Generate output file 
#---------------------------------------------------------

yaml_out_path = os.path.join(output_dir, "randomized_alchemy.yaml")
plugin_out_path = os.path.join(output_dir, "randomized_alchemy.omwaddon")

print(f"Generating output yaml: {yaml_out_path}")

yaml_out = open(yaml_out_path, mode = "w", buffering = 64*1024)
yaml_out.write(file_header.group())
yaml_out.write("\n")

for i in output_ingredients:
    yaml_out.write(i.header)
    if i.effects:
        yaml_out.write("\n")
        for e in i.effects:
            e.write_to(yaml_out, i.indent)
    else:
        yaml_out.write("[]\n")

    if i.tail:
        yaml_out.write(i.tail)
        yaml_out.write("\n")

yaml_out.close()

print(f"Converting yaml to plugin...")
run_result = subprocess.run(["./delta_plugin", "convert", "-o", f"{output_dir}", f"{yaml_out_path}"])
if run_result.returncode != 0:
    sys.exit("delta_plugin returned error. Aborting...")

if not keep_yaml:
    os.remove(yaml_out_path)

if not yaml_in_custom:
    os.remove(yaml_in_path)
    os.remove(plugin_in_path)

print("Finished")
