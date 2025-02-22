    // MISCELLANEOUS UTILS ------ ------ ------ ------ ------ */

    // a funciton that does nothing
    function noop() {}

    // generates a random id
    function random_id(prefix="") {
        var result           = prefix ;
        var characters       = 'abcdef0123456789';
        var charactersLength = characters.length;
        for ( var i = 0; i < 10; i++ ) { result += characters.charAt(Math.floor(Math.random() * charactersLength)); }
        return result;
    }

    // converts a ISO 8601 timestamp string into a human friendly format
    function date(isostring) {

        const date = new Date(isostring);

        const formattedDate = new Intl.DateTimeFormat('fr-FR', {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            timeZoneName: 'short'
        }).format(date);

        return formattedDate ;

    } 

    // Function to debounce a function
    function debounce(fn, delay = 300) {
        let timeout;
        return function(...args) {
            clearTimeout(timeout);
            timeout = setTimeout(() => fn(...args), delay);
        };
    }

    // Function to throttle a function
    function throttle(fn, wait = 50) {
        let lastTime = 0;
        let lastArgs = null;
        let timer    = null;

        return function(...args) {
            const now = Date.now();

            // Leading call if enough time has passed or if none so far
            if (!lastTime || now - lastTime >= wait) {
                fn(...args);
                lastTime = now;
                clearTimeout(timer);
                timer = setTimeout(() => {
                    if (lastArgs) {
                        fn(...lastArgs);
                    }
                    lastTime = 0;
                    lastArgs = null;
                }, wait);
            } else {
                // Store arguments for trailing call
                lastArgs = args;
            }
        };
    }

    function wait(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    // Function to hash any string
    function hashString(str) {
        let hash = 0;
        for (let i = 0; i < str.length; i++) {
            hash = str.charCodeAt(i) + ((hash << 5) - hash);
        }
        return hash;
    }


    // Function to find an object in an array by attribute value
    function find(array, attributeName, attributeValue) {
        return array.find(item => item[attributeName] === attributeValue);
    }

    // Object shortcuts
    function keys(obj)          { return Object.keys(obj) }
    function values(obj)        { return Object.values(obj) }
    function entries(obj)       { return Object.entries(obj) }
    function fromEntries(arr)   { return Object.fromEntries(arr) }

    // Turn Redis strings into JS boolean - and vice versa
    function boolify(str)       { return str === "True" }
    function stringify(bool)    { return bool ? "True" : "False" }
