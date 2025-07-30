# infra/terraform/main.tf

# vpc
resource "digitalocean_vpc" "main" {
  name   = "hissabi-vpc"
  region = var.region
}

# api droplet
resource "digitalocean_droplet" "api" {
  name     = "hissabi-api"
  region   = var.region
  size     = "s-1vcpu-1gb"
  image    = "docker-20-04"
  vpc_uuid = digitalocean_vpc.main.id
}

# worker droplet
resource "digitalocean_droplet" "worker" {
  name     = "hissabi-worker"
  region   = var.region
  size     = "s-1vcpu-1gb"
  image    = "docker-20-04"
  vpc_uuid = digitalocean_vpc.main.id
}

# managed Postgres cluster
resource "digitalocean_database_cluster" "postgres" {
  name     = "hissabi-db"
  engine   = "pg"
  version  = "16"
  size     = "db-s-1vcpu-1gb"
  region   = var.region
  node_count             = 1              # use node_count, not num_nodes
  private_network_uuid   = digitalocean_vpc.main.id  # attach to VPC
}

# managed Redis cluster (engine redis)
resource "digitalocean_database_cluster" "redis" {
  name     = "hissabi-redis"
  engine   = "redis"
  version  = "7"                         # Redis major version
  size     = "db-s-1vcpu-1gb"
  region   = var.region
  node_count             = 1
  private_network_uuid   = digitalocean_vpc.main.id
}

# spaces bucket
resource "digitalocean_spaces_bucket" "uploads" {
  name   = "hissabi-uploads"
  region = var.region
}
