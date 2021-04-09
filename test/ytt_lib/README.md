## How to use this library

Due to a `ytt` limitation, you need to symlink individual files into the directory of the configuration that wants
to use them. Example:
```
binary_archives
├── data
│   ├── orchestra
│   │   └── .orchestra
│   │       └── config
│   │           ├── builder.lib.yml -> ../../../../../ytt_lib/builder.lib.yml
│   │           └── components.yml
ytt_lib
├── builder.lib.yml
└── README.md
```

`components.yml` can import functions from `builder.lib.yml` like so:
```
#@ load("/builder.lib.yml", "component", "basic_build")
```
