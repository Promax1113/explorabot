
choice=$(gum choose broadcast create delete deactivate)
if [[ "$choice" == "broadcast" ]]; then
    connection=$(nmcli con | awk 'NR>1 {print $1}' | gum choose --header="select a connection to start up: ")
    nmcli connection up "$connection"
elif [[ "$choice" == "create" ]]; then
    name=$(gum input --prompt="hotspot name: " --placeholder="ArduRobot")
    device=$(nmcli device | awk 'NR>1 {print $1}' | gum choose --header="select a device to create the connection on:")
    nmcli connection add type wifi ifname "$device" mode ap con-name "$name" ssid "$name"

    choice=$(gum choose wpa rsn "rsn wpa")
    nmcli connection modify "$name" 802-11-wireless-security.key-mgmt wpa-psk

    nmcli connection modify "$name" 802-11-wireless-security.proto "$choice"
    
    choice=$(gum choose ccmp tkip)

    nmcli connection modify "$name" 802-11-wireless-security.pairwise "$choice"
    nmcli connection modify "$name" 802-11-wireless-security.group "$choice"
    password=$(gum input --password --placeholder "enter hotspot password")

    nmcli connection modify "$name" 802-11-wireless-security.psk "$password"

    nmcli connection modify "$name" ipv4.addresses 10.10.10.1/24 ipv4.method shared
elif [[ "$choice" == "delete" ]]; then
    connection=$(nmcli con | awk 'NR>1 {print $1}' | gum choose --header="select a connection to remove: ")
    if [[ -z "$connection" ]]; then
        exit
    fi


    if gum confirm "are you sure you want to delete $connection?"; then
        nmcli con delete "$connection"
    fi
elif [[ "$choice" == "deactivate" ]]; then
    connection=$(nmcli con | awk 'NR>1 {print $1}' | gum choose --header="select a connection to start up: ")
    nmcli connection down "$connection"
fi
