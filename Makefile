.PHONY: help test test-engine test-pytest bench bench-speed bench-corr evo warm-start clean

help:
	@echo "growth-os — common tasks"
	@echo ""
	@echo "  make test           Run all tests (engine self-tests + pytest)"
	@echo "  make test-engine    Run each engine module's self-test"
	@echo "  make test-pytest    Run the pytest suite"
	@echo "  make bench          Run both benchmarks (speed + correlation)"
	@echo "  make bench-speed    Benchmark simulator speed (μs per call)"
	@echo "  make bench-corr     Benchmark simulator ranking correlation"
	@echo "  make evo            Run the evolutionary loop for 20 iterations"
	@echo "  make warm-start     Run evo loop with Grok-mined priors (offline fallback if no key)"
	@echo "  make clean          Remove cached bytecode + build artifacts"

test: test-engine test-pytest

test-engine:
	@cd engine && for m in signal_weights.py twitter_simulator.py slot.py verifier.py results_log.py hypothesis_generator.py ab_tester.py grok_playbook_miner.py; do \
		echo "=== $$m ==="; \
		python3 $$m > /dev/null || { echo "FAILED: $$m"; exit 1; }; \
	done
	@echo "✓ all engine modules pass self-tests"

test-pytest:
	python3 -m pytest tests/ -q

bench: bench-speed bench-corr

bench-speed:
	python3 benchmarks/simulator_speed.py

bench-corr:
	python3 benchmarks/simulator_correlation.py

evo:
	cd engine && python3 evo_loop.py --iterations 20 --log /tmp/evo.tsv

warm-start:
	cd engine && python3 evo_loop.py --iterations 20 --log /tmp/evo.tsv \
		--warm-start memories_ai rerundotio physical_int

clean:
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name '.pytest_cache' -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name '.ruff_cache' -type d -exec rm -rf {} + 2>/dev/null || true
	rm -f /tmp/evo.tsv /tmp/evo_ci.tsv /tmp/evo_ws.tsv
