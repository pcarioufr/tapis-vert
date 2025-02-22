    // COOKIES ------ ------ ------ ------ ------ */

    class Cookies {
    
        constructor(){}

        set(cname, cvalue) {
            var d = new Date()
            d.setTime(d.getTime() + 365*24*60*60*1000 )
            document.cookie = `${cname}=${cvalue};expires=${d.toUTCString()};path=/`
        }

        get(cname) {
            var name = `${cname}=`
            var decodedCookie = decodeURIComponent(document.cookie);
            var ca = decodedCookie.split(';');
            for(var i = 0; i <ca.length; i++) {
                var c = ca[i];
                while (c.charAt(0) == ' ') { c = c.substring(1); }
                if (c.indexOf(name) == 0) { return c.substring(name.length, c.length); }
            }
            return "";
        }

        delete(cname) {
            document.cookie = `${cname}=;expires=Thu, 01 Jan 1970 00:00:00 UTC;path=/`;
        }

    }
