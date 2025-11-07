#!/bin/bash

GREEN='\033[0;32m'
GOLD='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}"
echo "████████╗██╗  ██╗ ██████╗ "
echo "╚══██╔══╝██║  ██║██╔═══██╗"
echo "   ██║   ███████║██║   ██║"
echo "   ██║   ██╔══██║██║   ██║"
echo "   ██║   ██║  ██║╚██████╔╝"
echo "   ╚═╝   ╚═╝  ╚═╝ ╚═════╝ "
echo -e "${GOLD}"
echo "╔═════════════════════════════╗"
echo "║   Instalador de Requisitos  ║"
echo "║   By: LEATHER FACE          ║"
echo "╚═════════════════════════════╝"
echo -e "${NC}"

progress() {
    local width=50
    local percentage=$1
    local filled=$((percentage * width / 100))
    local empty=$((width - filled))
    
    printf "\r[${GREEN}"
    printf "%${filled}s" '' | tr ' ' '█'
    printf "${NC}"
    printf "%${empty}s" '' | tr ' ' '░'
    printf "] ${percentage}%%"
}

echo -e "\n${GREEN}[*]${NC} Instalando requisitos...\n"

total=5
count=0

if ! command -v python3 &> /dev/null; then
    sudo apt-get install python3 -y
fi
progress $((++count * 100 / total))

if ! command -v pip3 &> /dev/null; then
    sudo apt-get install python3-pip -y
fi
progress $((++count * 100 / total))

echo -e "\n\n${GREEN}[*]${NC} Instalando dependencias de Python..."
pip3 install requests &> /dev/null
progress $((++count * 100 / total))

pip3 install urllib3 &> /dev/null
progress $((++count * 100 / total))

pip3 install concurrent.futures &> /dev/null
progress $((++count * 100 / total))

echo -e "\n\n${GREEN}[✓]${NC} Instalación completada!"
echo -e "${GREEN}[*]${NC} Ejecute: python3 tho.py"

chmod +x tho.py

exit 0
