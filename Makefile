# Makefile for MedType Benchmarks

# PubMedDS doesn't have category information and isn't in
# PubAnnotator format. This script fixes both of these issues.
input/split_11.pubannotator.jsonl: input/split_11.txt venv-activate
	python scripts/pubmedds2pubannotator.py $< -O $@

# Create a virtual environment for Python work.
venv:
	python3 -m venv venv
	. ./venv/bin/activate
	pip3 install -r requirements.txt

venv-activate: venv
	. ./venv/bin/activate

.PHONY: venv-activate

# Clean outputs.
clean:
	rm -rf venv
	rm input/split_11.pubannotator.json
.PHONY: clean
