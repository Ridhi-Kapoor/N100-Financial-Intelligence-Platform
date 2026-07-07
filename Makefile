install:
	pip install -r requirements.txt

test:
	pytest

format:
	black .

run:
	python main.py