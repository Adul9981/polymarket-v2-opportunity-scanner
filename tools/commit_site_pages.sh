#!/bin/bash
# 服务器端：提交 site_repo 中的指定页面并推送（deploy key）。
# 用法：bash tools/commit_site_pages.sh "提交说明" file1 file2 ...
set -euo pipefail
cd /opt/danmu-intel/site_repo
export GIT_SSH_COMMAND="ssh -i /root/.ssh/github_deploy -o StrictHostKeyChecking=accept-new"
git add "${@:2}"
git commit -m "$1" -q
git push -q origin main
echo "committed and pushed"
