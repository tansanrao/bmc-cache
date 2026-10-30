# SPDX-FileCopyrightText: Copyright (c) 2021 Orange
# SPDX-License-Identifier: LGPL-2.1-only

# Use the current kernel tree's libbpf and system UAPI headers.
LINUX_PATH ?= ../../linux
OUTPUT ?= ../../build/bmc
CLANG ?= clang
CC ?= gcc
CFLAGS ?= -O2 -g -Wall -Wextra -Werror

OUTPUT := $(abspath $(OUTPUT))
LIBBPF_DIR := $(OUTPUT)/libbpf
LIBBPF := $(LIBBPF_DIR)/libbpf.a
INCLUDES := -I$(LIBBPF_DIR)/include
ARCH_INCLUDE := /usr/include/$(shell $(CC) -dumpmachine)

.PHONY: all clean
all: $(OUTPUT)/bmc $(OUTPUT)/bmc_kern.o

$(LIBBPF):
	mkdir -p $(LIBBPF_DIR)
	$(MAKE) -C $(LINUX_PATH)/tools/lib/bpf OUTPUT=$(LIBBPF_DIR)/ \
		BUILD_STATIC_ONLY=1 DESTDIR=$(LIBBPF_DIR) prefix= \
		libdir=/lib includedir=/include all install_headers

$(OUTPUT)/bmc: bmc_user.c bmc_common.h $(LIBBPF)
	$(CC) $(CFLAGS) $(INCLUDES) $< $(LIBBPF) -lelf -lz -o $@

$(OUTPUT)/bmc_kern.o: bmc_kern.c bmc_common.h $(LIBBPF)
	$(CLANG) -target bpf -O2 -g -Wall -Werror $(INCLUDES) \
		-Wno-compare-distinct-pointer-types -I$(ARCH_INCLUDE) -c $< -o $@

clean:
	rm -f $(OUTPUT)/bmc $(OUTPUT)/bmc_kern.o
