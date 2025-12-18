#!/home/kromgart/.cargo/bin/nu


def main [] {
  mkdir deskilled_books.tmp
  cd deskilled_books.tmp

  delta_plugin filter --all -o ./all_books.omwaddon match Book
  delta_plugin convert -o . ./all_books.omwaddon

  mut plugin = open ./all_books.yaml
  $plugin.records = (
    $plugin
    | get records
    | transpose
    | where { 'skill' in ($in.column1 | columns) }
    | reject column1.skill
    | transpose -rd
  )

  $plugin | save -f ./deskilled_books.yaml

  delta_plugin convert -o ../ ./deskilled_books.yaml

  rm -rf ./deskilled_books.tmp
  
}

