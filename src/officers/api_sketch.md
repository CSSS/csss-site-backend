# sfucsss.org REST api sketches

## api.sfucsss.org/officers

### GET current/
- Information for all the current officers to display on the page
- NOTE: images are stored in github for the time being, but we should move them
- QUESTION: how full is the digitalocean hdd?
- TODO: store different sized images 

response:
```json
{ 
    "officers": [
        {
            "position": String,
            "start_date": Date,

            "legal_name": String,
            "nickname": String,
            "discord_name": String,
            "discord_nickname": String,

            "favourite_courses": [ 
                String,
                String
            ],
            "favourite_languages": [ 
                String,
                String
            ],

            "sfu_email": String,
            "biography": String,

            "photo_url": String,

            // (returns empty unless you're authenticated and a current Officer)
            "computing_id": String,
            "phone_number": String,
            "github_username": String,
            "gmail": String, // TODO: change to "personal_email" if that works
        },
        ...
    ]
}
```

### GET past/
- Information from past exec terms. If year is not included, all years will be returned. If semester is not included, all semesters that year will be returned. If semester is given, but year is not, return all years and all semesters.
- ?year=
- ?semester=
- TODO: consider letting year be a ranged parameter?

response:
```json
{ 
    "officers": [
        {
            "position": String,
            "start_date": Date,

            "legal_name": String,
            "nickname": String,
            "discord_name": String,
            "discord_nickname": String,

            "favourite_courses": [ 
                String,
                String
            ],
            "favourite_languages": [ 
                String,
                String
            ],

            "sfu_email": String,
            "biography": String,

            "photo_url": String,

            // (returns empty unless you're authenticated and a current Officer)
            "computing_id": String,
            "phone_number": String,
            "github_username": String,
            "gmail": String, // TODO: change to "personal_email" if that works
        },
        ...
    ]
}
```

### POST enter_info/
- After elections, officer computing ids are input into our system. If you have been elected as a new officer, you may authenticate with SFU CAS, then input your information & the valid token for us.
- HEADER sfu_auth_token 
  - TODO: is this how CAS authentication works? How can we ensure a browser user knows the password associated with an sfu computing id

request:
```json
{
    "legal_name": String,
    "nickname": String, // empty string means no nickname
    "discord_name": String,

    "favourite_courses": [ 
        String,
        String
    ],
    "favourite_languages": [
        String,
        String
    ],

    "biography": String,

    // "upload_photo": Bytes, // TODO: or however this works?

    "computing_id": String,
    "phone_number": String,
    "github_username": String,
    "gmail": String, // TODO: change to "personal_email" if that works
    "gmail_auth_code": String,
},
```

response:
```json
{
    "success": Boolean, // TODO: we may or may not need interactive validation of each of the names & emails
    "reason": {
        "invalid_discord_user": Boolean,
        "invalid_computing_id": Boolean,
        "invalid_gmail_auth_code": Boolean,
        "invalid_phone_number": Boolean,
    }
}
```

### GET my_info/
- Get info about whether you are still an executive or not / what your position is
- HEADER sfu_auth_token 
- ?computing_id=

response:
```json
{
    "is_officer": Boolean,
    // (returns empty unless you're authenticated and a current Officer)
    "info": {
        "position": String,
        "start_date": Date,

        "legal_name": String,
        "nickname": String,
        "discord_name": String,
        "discord_nickname": String,

        "favourite_courses": [ 
            String,
            String
        ],
        "favourite_languages": [ 
            String,
            String
        ],

        "sfu_email": String,
        "biography": String,

        "photo_url": String,

        "computing_id": String,
        "phone_number": String,
        "github_username": String,
        "gmail": String, // TODO: change to "personal_email" if that works
    },
},
```

### POST new_officer/
- Only the sysadmin, president, or DoA can submit this request. It will usually be the DoA. Updates the system with a new officer, and enables the user to login to the system to input their information.
- HEADER sfu_auth_token 
- ?computing_id=

request:
```json
{
    "position": String,
    "start_date": Date,
    "computing_id": String,
}
```

response:
```json
{
    "success": Boolean
}
```

### DELETE new_officer/
- Only the sysadmin, president, or DoA can submit this request. It will usually be the DoA. Removes the officer from the system entirely. BE CAREFUL WITH THIS OPTION aaaaaaaaaaaaaaaaaa
- HEADER sfu_auth_token 
- ?computing_id=

request:
```json
{
    "position": String,
    "start_date": Date,
    "computing_id": String,    
}
```

response:
```json
{
    "success": Boolean
}
```

### POST update_officer/
- Only the sysadmin, president, or DoA can submit this request. It will usually be the DoA. Modify the stored info of an existing officer.
- HEADER sfu_auth_token 
- ?computing_id=

request:
```json
{
    "current": {
        "position": String,
        "start_date": Date,
        "computing_id": String,
    },
    "new": {
        "position": String,
        "start_date": Date,

        "legal_name": String,
        "nickname": String,
        "discord_name": String,
        "discord_nickname": String,

        "favourite_courses": [ 
            String,
            String
        ],
        "favourite_languages": [ 
            String,
            String
        ],

        "sfu_email": String,
        "biography": String,

        "photo_url": String,

        // (returns empty unless you're authenticated and a current Officer)
        "computing_id": String,
        "phone_number": String,
        "github_username": String,
        "gmail": String, // TODO: change to "personal_email" if that works
    }
}
```

response:
```json
{
    "success": Boolean
    // TODO: might do a validity check here, depending on implementation
}
```

