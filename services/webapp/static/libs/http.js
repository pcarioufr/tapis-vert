    // HTTP UTILS ------ ------ ------ ------ ------ */

    function handle_response(r, ignore4xx=false) { 
        if (r.status >= 500) { throw "oups, c'est cassé..." }
        if (!ignore4xx){
            if (r.status == 401) { throw "oups, ce n'est pas autorisé..." }
            if (r.status == 403) { throw "oups, ce n'est pas autorisé..." }
            if (r.status >= 400) { throw "oups, c'est est cassé..." }
        }
        return r
    }

    function imageAssign(div,blob) {
        div.setAttribute("src",""+URL.createObjectURL(blob))
    }


    
    async function call(method, route, params = {}, headers = {}, body = {} ) {

        // Build query string manually
        let first = true;
        Object.keys(params).forEach( key => {
            if (first) { route += '?'; first = false;} 
            else       { route += '&'; }
            route += `${key}=${params[key]}`;
        });

        if (method !== 'GET' && Object.keys(body).length > 0) {
            headers['Content-Type'] = 'application/json';
            body = JSON.stringify(body);
        } else {
            body = null; // e.g. no body for GET or if no body fields were provided
        }

        try {
            const resp = await fetch(route, { method: method, headers: headers, body: body });
            return handle_response(resp);
        } catch (error) {
            throw error; /* TODO */ // currently re-throw the error
        }
    }
