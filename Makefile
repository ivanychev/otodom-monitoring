


format:
	isort otodom
	pycln otodom
	pyupgrade --py312-plus `find otodom -name "*.py"` || true
	black otodom
