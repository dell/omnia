.PHONY: all clean

PYTHON ?= python3

# Check if a file named "ldms_machine_config.json" exists
ifeq (,$(wildcard ldms_machine_config.json))
    $(error ldms_machine_config.json is missing! Aborting. Create file.)
endif

# Main target
all: manifest.yaml

# Define products to be cleaned
products = out_dir \
           nersc-ldms-aggr/templates/cm.nersc-ldms-bin.yaml \
           nersc-ldms-aggr/templates/cm.nersc-ldms-conf.yaml \
           values.yaml \
           manifest.yaml

# Declare generated files depend on a common marker
out_dir/cm.nersc-ldms-bin.yaml: out_dir/.generated

out_dir/cm.nersc-ldms-conf.yaml: out_dir/.generated

out_dir/nersc-ldmsd-port-map.json: out_dir/.generated

# Marker target to run the init scripts only once
out_dir/.generated:
	@echo "Running make_host_map.dell.py"
	$(PYTHON) make_host_map.dell.py --config=ldms_machine_config.json
	@echo "Running nersc_ldms_make_ldms_config.py --config=ldms_machine_config.json"
	$(PYTHON) nersc_ldms_make_ldms_config.py --config=ldms_machine_config.json
	touch $@

# Copy templates from generated files
nersc-ldms-aggr/templates/cm.nersc-ldms-bin.yaml: out_dir/cm.nersc-ldms-bin.yaml
	cp -f $< $@

nersc-ldms-aggr/templates/cm.nersc-ldms-conf.yaml: out_dir/cm.nersc-ldms-conf.yaml
	cp -f $< $@

# Generate manifest.yaml from the template
manifest.yaml: manifest.yaml.in out_dir/cm.nersc-ldms-conf.yaml out_dir/cm.nersc-ldms-bin.yaml
	$(PYTHON) mkmanifest.py > manifest.yaml

# Clean up generated files
clean:
	rm -rf $(products)
