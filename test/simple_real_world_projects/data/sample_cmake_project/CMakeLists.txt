cmake_minimum_required(VERSION 3.10)

project("SampleProject")

# add the executable
add_executable(testprogram test.c)

install(TARGETS testprogram DESTINATION bin)
