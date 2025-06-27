# vpc
resource "digitalocean_vpc" "main" {
  name   = "hissabi-vpc"
  region = var.region
}

# droplets
resource "digitalocean_droplet" "api" {
  name     = "hissabi-api"
  region   = var.region
  size     = "s-1vcpu-1gb"
  image    = "docker-20-04"
  vpc_uuid = digitalocean_vpc.main.id
}

resource "digitalocean_droplet" "worker" {
  name     = "hissabi-worker"
  region   = var.region
  size     = "s-1vcpu-1gb"
  image    = "docker-20-04"
  vpc_uuid = digitalocean_vpc.main.id
}

# managed postgres
resource "digitalocean_database_cluster" "postgres" {
  name       = "hissabi-db"
  engine     = "pg"
  version    = "16"
  size       = "db-s-1vcpu-1gb"
  region     = var.region
  num_nodes  = 1
  vpc_uuid   = digitalocean_vpc.main.id
}

# managed redis
resource "digitalocean_redis_database" "cache" {
  name     = "hissabi-redis"
  engine   = "redis"
  size     = "db-s-1vcpu-1gb"
  region   = var.region
  vpc_uuid = digitalocean_vpc.main.id
}

# spaces bucket
resource "digitalocean_spaces_bucket" "uploads" {
  name   = "hissabi-uploads"
  region = var.region
}
