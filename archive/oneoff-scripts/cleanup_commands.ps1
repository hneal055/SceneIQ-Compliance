# Generated Cleanup Commands - Review before executing!
# Run each section carefully and verify results


# Remove backup directories from git
git rm -r --cached backup_20260110_140811/
git rm -r --cached backup_20260111_074042/
git commit -m 'chore: remove backup directories from version control'

# Move test files to tests directory
# First create fixtures directory if needed
New-Item -ItemType Directory -Force -Path tests/fixtures
git mv test_reportlab.py tests/
git mv test_excel.xlsx tests/fixtures/
git mv test.pdf tests/fixtures/
git mv sample.pdf tests/fixtures/
git commit -m 'chore: organize test files into tests directory'
