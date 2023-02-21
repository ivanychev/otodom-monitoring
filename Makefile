


format:
	isort otodom
	pycln otodom
	pyupgrade --py311-plus `find otodom -name "*.py"` || true
	black otodom
