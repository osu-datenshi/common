# low byte 0
USER_PUBLIC               = 1 <<  0
USER_NORMAL               = 1 <<  1
USER_DONOR                = 1 <<  2
ADMIN_ACCESS_RAP          = 1 <<  3
# hi byte 0
ADMIN_MANAGE_USERS        = 1 <<  4
ADMIN_BAN_USERS           = 1 <<  5
ADMIN_SILENCE_USERS       = 1 <<  6
ADMIN_WIPE_USERS          = 1 <<  7
# low byte 1
ADMIN_MANAGE_BEATMAPS     = 1 <<  8
ADMIN_MANAGE_SERVERS      = 1 <<  9
ADMIN_MANAGE_SETTINGS     = 1 << 10
ADMIN_MANAGE_BETAKEYS     = 1 << 11
#
ADMIN_MANAGE_REPORTS      = 1 << 12
ADMIN_MANAGE_DOCS         = 1 << 13
ADMIN_MANAGE_BADGES       = 1 << 14
ADMIN_VIEW_RAP_LOGS       = 1 << 15
# low byte 2
ADMIN_MANAGE_PRIVILEGES   = 1 << 16
ADMIN_SEND_ALERTS         = 1 << 17
ADMIN_CHAT_MOD            = 1 << 18
ADMIN_KICK_USERS          = 1 << 19
#
USER_PENDING_VERIFICATION = 1 << 20
USER_TOURNAMENT_STAFF     = 1 << 21
ADMIN_CAKER               = 1 << 22
ADMIN_BYPASS_CHECKS       = 1 << 23
# low byte 3
# AUTORANK_MANAGE, this is an extremely critical role, so just BAT/BN won't do.
ADMIN_MANAGE_AUTORANK     = 1 << 24
# groups
ADMIN_BYPASS_MODERATION   = ADMIN_CHAT_MOD | ADMIN_BYPASS_CHECKS
