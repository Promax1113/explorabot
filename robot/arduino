#!/bin/bash


upload() {
  local ports=($(ls /dev/ttyACM* 2>/dev/null))

  if [ ${#ports[@]} -eq 0 ]; then
    gum style --foreground 1 "no arduino boards found"
    return 1
  fi
  if [ ${#ports[@]} -eq 1 ]; then
    port="${ports[0]}"
    echo "selected upload port as $port" 
  else
    port=$(gum choose "$ports")
  fi

  arduino-cli upload -p "$port" --fqbn "$fqbn" "$file" >> /dev/null
  echo "done uploading."
}

compile(){
  arduino-cli compile --fqbn "$fqbn" "$file" >> /dev/null
  echo "done compiling."

}


action=$(gum choose "compile and upload" "compile" "upload")

fqbn=$(arduino-cli board list --json | jq -r '.detected_ports[].matching_boards[]?.fqbn')
  
file=$(gum file)
[[ "$file" == *.ino ]] || {
  gum style --foreground 1 "not a sketch file"
  exit 1
}


if [[ "$action" = "upload"  ]]; then
  upload
elif [[ "$action" = "compile" ]]; then
  compile
elif [[ "$action" = "compile and upload" ]]; then
  compile
  upload
else
  exit 1
fi
