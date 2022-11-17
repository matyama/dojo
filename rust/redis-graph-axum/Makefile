.PHONY: crawl dungeon

# requires: https://github.com/ducaale/xh

ADDR :=
PORT := 3000

check:
	@xh $(ADDR):$${SERVER_PORT:-$(PORT)}

crawl:
	@xh $(ADDR):$${SERVER_PORT:-$(PORT)}/$@

dungeon: SIZE := 10
dungeon: MAXGP := 10
dungeon: TREASURES := 3
dungeon:
	@xh put $(ADDR):$${SERVER_PORT:-$(PORT)}/$@ \
		size==$(SIZE) maxgp==$(MAXGP) max_treasures==$(TREASURES)

