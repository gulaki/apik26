.PHONY: test demo clean

test:
	python -m pytest

demo:
	mkdir -p build
	python -m apik26.cli examples/fibonacci.apik -o build/fibonacci.c --build make --build-output build/Makefile

clean:
	rm -rf build/*.c build/Makefile build/*.ninja build/fibonacci
