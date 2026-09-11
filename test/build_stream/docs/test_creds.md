# Credential stores

Build Stream automation keeps transport and product credentials separate.

## OIM transport credential

`test_creds.yml` and `.test_creds.key` are local, gitignored files used only
for password-based SSH to a remote execution OIM. Create them with:

```bash
./setup_env.sh --set-creds
```

For automation, pipe the password through standard input:

```bash
approved-secret-provider | ./setup_env.sh --creds-stdin
```

## Build Stream product credentials

Run the following on the execution OIM after sourcing
`/etc/omnia/omnia.env`:

```bash
./setup_env.sh --set-domain-creds
```

The encrypted credential pair is written to:

```text
$OMNIA_DATA_PATH/build_stream/input/$OMNIA_PROJECT_NAME/
├── build_stream_credentials.yml
└── .build_stream_credentials_key
```

Supported fields are the GitLab root and SSH passwords, required BSM
authentication username/password, and optional Postgres username/password.
The setup helper derives and stores the required Argon2 password hash without
printing the plaintext password. Non-interactive configuration accepts a
bounded JSON payload on standard input through `--domain-creds-stdin`.

Credentials are never generated in datasets or synchronized by the framework.
