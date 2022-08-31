


format:
	isort otodom
	pycln otodom
	pyupgrade --py310-plus `find otodom -name "*.py"` || true
	black otodom