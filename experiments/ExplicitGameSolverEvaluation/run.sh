set -e

# Get list of all specification versions
rm -f *.txt *.xml
cd ../..
mkdir -p /tmp/all_versions_exported
rm /tmp/all_versions_exported/*.txt
rm /tmp/all_versions_exported/*.xml
tools/git_all_versions.sh examples/guis/ExpenseSplit/app/synthspecs/mainActivitySpec.txt
tools/git_all_versions.sh examples/guis/ExpenseSplit/app/src/main/res/layout/content_main.xml
cd experiments/ExplicitGameSolverEvaluation
cp /tmp/all_versions_exported/*.txt .
cp /tmp/all_versions_exported/*.xml .

