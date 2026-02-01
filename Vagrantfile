# -*- mode: ruby -*-
# vi: set ft=ruby :

# yolo-cage VM
#
# Usage:
#   vagrant up         # Build the VM
#   vagrant ssh        # Connect to VM
#   vagrant destroy -f # Delete VM

# Runtime name derived from Instance name (set by host CLI)
# Falls back to "default" for standalone/dev usage or backward compatibility
INSTANCE_NAME = ENV["YOLO_CAGE_INSTANCE"] || "default"

# Backward compatibility: if old-style VM exists (.vagrant/machines/default),
# use "default" instead of instance name to avoid orphaning existing VMs
if File.directory?(".vagrant/machines/default") && !File.directory?(".vagrant/machines/#{INSTANCE_NAME}")
  MACHINE_NAME = "default"
else
  MACHINE_NAME = INSTANCE_NAME
end

Vagrant.configure("2") do |config|
  config.vm.define MACHINE_NAME do |machine|
    # Use ARM64 box on Apple Silicon, x86 box elsewhere
    if RUBY_PLATFORM.include?("arm64") || RUBY_PLATFORM.include?("aarch64")
      machine.vm.box = "perk/ubuntu-2204-arm64"
    else
      machine.vm.box = "generic/ubuntu2204"
    end
    machine.vm.hostname = "yolo-cage"

    # libvirt provider (Linux)
    machine.vm.provider "libvirt" do |lv|
      lv.memory = 8192
      lv.cpus = 4
    end

    # QEMU provider (macOS Apple Silicon)
    machine.vm.provider "qemu" do |qe|
      qe.memory = "8G"
      qe.smp = 4
    end

    # Sync repo into VM
    machine.vm.synced_folder ".", "/home/vagrant/yolo-cage", type: "rsync"

    # Provision: run build script from within the synced repo
    machine.vm.provision "shell", inline: "cd /home/vagrant/yolo-cage && ./scripts/build-release.sh"
  end
end
