.PHONY: setup install clean

setup:
	@docker swarm init
	@docker service create \
		--name registry \
		--publish published=5000,target=5000 \
		registry:2

install:
	@docker-compose build
	@docker-compose push
	@docker stack deploy -c docker-compose.yml redis-pubsub

clean:
	@docker stack rm redis-pubsub
	@docker service rm registry
	@docker swarm leave --force

