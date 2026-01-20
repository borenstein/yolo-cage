# -*- mode: ruby -*-
# vi: set ft=ruby :

# yolo-cage VM
#
# Usage:
#   vagrant up         # Build the VM
#   vagrant ssh        # Connect to VM
#   vagrant destroy -f # Delete VM

Vagrant.configure("2") do |config|
  config.vm.box = "generic/ubuntu2204"
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
    qe.arch = "aarch64"
  end

  # Sync repo into VM
  config.vm.synced_folder ".", "/home/vagrant/yolo-cage", type: "rsync"

  # Provision: run build script from within the synced repo
  config.vm.provision "shell", inline: "cd /home/vagrant/yolo-cage && ./scripts/build-release.sh"
end
