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

  # Use libvirt provider (for headless servers)
  config.vm.provider "libvirt" do |lv|
    lv.memory = 32768
    lv.cpus = 8
  end

  # Sync repo into VM
  config.vm.synced_folder ".", "/home/vagrant/yolo-cage", type: "rsync"

  # Provision: run build script from within the synced repo
  config.vm.provision "shell", inline: "cd /home/vagrant/yolo-cage && ./scripts/build-release.sh"

  config.vm.post_up_message = <<-MSG
    yolo-cage VM ready.

    vagrant ssh
    cp /home/vagrant/yolo-cage/config.yaml.example ~/.yolo-cage/config.yaml
    nano ~/.yolo-cage/config.yaml   # Add your GitHub PAT and repo URL
    yolo-cage-configure
    yolo-cage create my-branch
  MSG
end
