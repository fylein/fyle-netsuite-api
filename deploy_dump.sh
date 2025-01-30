if [ -z "$1" ]; then
  echo "Usage: sh $0 '2024-12-09'"
  exit 1
fi

base_url="https://github.com/fylein/fyle-netsuite-api/commit"
branch_name=$(git rev-parse --abbrev-ref HEAD)

git log --since="$1" --pretty=format:"$base_url/%H,%an,%ad,%s,$branch_name,netsuite-api" > commits.csv

open commits.csv
