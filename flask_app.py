# Copyright (C) 2020 James Ravindran
# SPDX-License-Identifier: AGPL-3.0-or-later

from leaderboards import *

db.create_all()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=80)