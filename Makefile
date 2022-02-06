# Makefile for MedType Benchmarks
#
RUNVENV=. ./venv/bin/activate &&

# PubMedDS doesn't have category information and isn't in
# PubAnnotator format. This script fixes both of these issues.
pubannotator/split_11.pubannotator.jsonl: input/split_11.txt venv
	$(RUNVENV) python scripts/pubmedds2pubannotator.py --normalize $< -O $@

# Create a virtual environment for Python work.
venv:
	python3 -m venv venv
	$(RUNVENV) pip3 install -r requirements.txt

# Clean outputs.
clean:
	rm -rf venv
	rm input/split_11.pubannotator.json
.PHONY: clean
