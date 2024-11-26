#compdef trogdor t

_trogdor() {
  local cur prev services all_services commands wordfile

  # Current word and previous word
  cur=$words[CURRENT]
  prev=$words[CURRENT-1]

  # Path to trogdor executable
  wordfile=$(which trogdor)

  # Define commands
  commands=("start" "stop" "restart" "status")

  # Exclude already used words from services
  services=($("${wordfile}" list))

  # Provide suggestions based on previous word
  if [[ " ${commands[@]} " == *" $prev "* ]]; then
    _values "services" $services
  else
    _values "commands" $commands
  fi
}

compdef _trogdor trogdor t