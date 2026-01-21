# -*- mode: ruby -*-
# vi: set ft=ruby :

# yolo-cage VM
#
# Usage:
#   vagrant up         # Build the VM
#   vagrant ssh        # Connect to VM
#   vagrant destroy -f # Delete VM

Vagrant.configure("2") do |config|
  # Use ARM64 box on Apple Silicon, x86 box elsewhere
  if RUBY_PLATFORM.include?("arm64") || RUBY_PLATFORM.include?("aarch64")
    config.vm.box = "perk/ubuntu-2204-arm64"
  else
    config.vm.box = "generic/ubuntu2204"
  end
  config.vm.hostname = "yolo-cage"

  # libvirt provider (Linux)
  config.vm.provider "libvirt" do |lv|
    lv.memory = 8192
    lv.cpus = 4
  end

  # QEMU provider (macOS Apple Silicon)
  config.vm.provider "qemu" do |qe|
    qe.memory = "8G"
    qe.smp = 4
  end

  # Sync repo into VM
  config.vm.synced_folder ".", "/home/vagrant/yolo-cage", type: "rsync"

  # Provision: run build script from within the synced repo
  config.vm.provision "shell", inline: "cd /home/vagrant/yolo-cage && ./scripts/build-release.sh"
end
