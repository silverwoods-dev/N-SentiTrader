#!/bin/bash
# N-SentiTrader Anti-Blocking: Cloudflare WARP Installation Script
# Reference: https://pkg.cloudflareclient.com/

set -e

echo "--- Adding Cloudflare GPG Key ---"
curl -fsSL https://pkg.cloudflareclient.com/pubkey.gpg | sudo gpg --yes --dearmor --output /usr/share/keyrings/cloudflare-warp-archive-keyring.gpg

echo "--- Adding Cloudflare Repository ---"
echo "deb [signed-by=/usr/share/keyrings/cloudflare-warp-archive-keyring.gpg] https://pkg.cloudflareclient.com/ $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/cloudflare-client.list

echo "--- Updating Package List & Installing Cloudflare WARP ---"
sudo apt-get update
sudo apt-get install -y cloudflare-warp

echo "--- Registration & Configuration ---"
echo "필요시 다음 명령어를 수동으로 실행하여 설정을 완료하세요:"
echo "1. warp-cli registration new"
echo "2. warp-cli mode proxy"
echo "3. warp-cli connect"

echo "--- Verification ---"
echo "현재 상태 확인: warp-cli status"
echo "프록시 동작 확인: curl -x socks5h://127.0.0.1:40000 https://www.cloudflare.com/cdn-cgi/trace | grep warp"

echo "Installation script completed."
