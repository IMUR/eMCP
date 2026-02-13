[Unit]
Description=Watch for eMCP docker-compose reload trigger

[Path]
PathModified=__EMCP_ROOT__/.reload-trigger
Unit=emcp-reload.service

[Install]
WantedBy=multi-user.target
