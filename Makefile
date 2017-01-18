help:
	@echo "  info        show information on current sys config"
	@echo "  clean       remove unwanted stuff"
	@echo "  test        run tests"
	@echo "  lint        run linter"
	@echo "  notebook    run a jupyter notebook"
	@echo "  lowres      make a lowres gif"
	@echo "  deploy      deploy bot to server"

test:
	PYTHONPATH=. py.test

info:
	python --version
	pyenv --version
	pip --version

clean:
	rm -fr build
	rm -fr dist
	find . -name '*.pyc' -exec rm -f {} \;
	find . -name '*.pyo' -exec rm -f {} \;
	find . -name '*~' ! -name '*.un~' -exec rm -f {} \;
	rm -f lowres/*.png

lint:
	pycodestyle --config=setup.cfg

notebook:
	jupyter notebook --no-browser

tweet:
	python -c 'import himawari_lowres; himawari_lowres.main()'

.PHONY: hires
hires:
	ansible-playbook -i ansible/hosts ansible/hires.yml --vault-password-file ~/.vault_pass.txt

.PHONY: lowres
lowres:
	ansible-playbook -i ansible/hosts ansible/himawari.yml --vault-password-file ~/.vault_pass.txt
