## omw_random_alchemy

This is a python script that can generate a new plugin file, where effects on alchemy ingredients are randomized. Currently the randimization keeps the total amount and types of effects same as in your modpack, but it shuffles them between ingredients. So if some ingredient has a certain effect, it will not be gone from the randomized output. And it will not add any effect to ingredient, if none of ingredients had such effect before.

To use this you need [delta_plugin](https://gitlab.com/portmod/delta-plugin) and python3 installed. The script uses delta_plugin to convert the ingredients data to yaml format, modifies that yaml file, and then uses delta_plugin again to generate a new *.omwaddon file.

### Usage
Put the omw_random_alchemy.py into the directory with delta_plugin and run:

```shell
$> python3 omw_random_alchemy.py --min-effects 2 --ignore-food --no-loners
Generating plugin with all ingredients...
WARN Records of type: "LUAL" are not yet supported and will be skipped
Writing to file ./tmp_source_alchemy.omwaddon...
Converting plugin with to yaml...
Writing result to ./tmp_source_alchemy.yaml...
Warning: ingredient hb_baitrandom doesn't have an icon
Warning: ingredient hb_hemolymph doesn't have a name
836 ingredients (with 66 clones) will be updated, 64 will be kept intact
Adding 20 effects to the effects pool due to --no-loners argument
Collected 3021 existing effects. The most frequent effect (RestoreFatigue) is used 146 times
Assigning at least 2 effect(s) to each ingredient, starting from most frequent ones...
Applied 1672 effects evenly onto 836 ingredients
Redistributing remaining effects...
Generating output yaml: ./randomized_alchemy.yaml
Converting yaml to plugin...
WARN Records of type: "LUAL" are not yet supported and will be skipped
Writing to file ./randomized_alchemy.omwaddon...
Finished
```

Now you can move the randomized_alchemy.omwaddon to your mod folders and enable it as you usually do with your mods.

Result (look at that stoneflower...):

![Ingredients with randomized effects](https://github.com/Kromgart/omw_random_alchemy/blob/main/rand_alch.png "Ingredients with randomized effects")

## Options

The script has some options. You can see them and their short description if you run "python3 ./omw_random_alchemy.py --help"

```sh
usage: omw_random_alchemy.py [-h] [--min-effects {1,2,3}] [--keep-yaml] [--ignore-food] [--no-loners] [--output-dir OUTPUT_DIR]
```

### --min-effects
  Can be 1, 2 or 3. The randomization will try to ensure that each updated ingredient has at least this amount of effects.

### --keep-yaml
  If you set this flag, the yaml file which contains all randomized results will not be deleted during cleanup.

### --ignore-food
  This flag prevents certain ingredients from participating in the process. More specifically it excludes any ingredient that has only one effect, and that effect is RestoreFatigue (this is usually the case for stuff considered 'food', like breads). Don't use this flag if you are fine with having poisonous bread that gives you levitation or drains endurance.

### --no-loners
  Depending on your modpack some effects will be present only on one ingredient. This makes it impossible to create a potion of such effect (you need at least two different ingredients with the same effect for that). This flag takes pity on those unfortunate effects and during randomization proces assigns such effect to TWO ingredients instead of one. This makes it theoretically possible to create potions of such effect (if you manage to procure the necessary ingredients of course)

### -i, --input-yaml
  This option allows to reuse existing .yaml file and skip the first step (exporting ingredients data by delta_plugin)

### --output-dir OUTPUT_DIR
  By default the script generates intermediate and resulting files in the directory where it is run. You can override this with this option (but create the directory beforehand)

## Known issues

Before the randomization there can be few ingredients without effects at all, like AB_IngFood_DoughRolled, or TR_m2_q_22_Dust. Those are not modified by us and are kept intact.
