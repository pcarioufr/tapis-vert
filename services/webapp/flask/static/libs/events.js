// EVENTS ------ ------ ------ ------ ------ */

    /**
    * Each listener is stored as an object:
    * {
    *   listenerId: string,
    *   pattern: string,  // can be exact name or pattern with wildcards
    *   callback: function
    * }
    */
    const LISTENERS = [];
    let EVENT_QUEUE = [];

    /**
    * Fire: triggers any listener whose pattern matches the eventName.
    * @param {string} throwerId
    * @param {string} eventName
    * @param {*} data
    */
    function fire(throwerId, eventName, data = null) {
        let matched = false;
        // Loop through all listener entries
        LISTENERS.forEach(({ listenerId, pattern, callback }) => {
            if (eventMatchesPattern(eventName, pattern)) {
                callback.call(this, throwerId, data, eventName);
                matched = true;
            }
        });
        if (!matched) {
            EVENT_QUEUE.push({ throwerId, eventName, data });
            console.log(`Event "${eventName}" queued.`);
        }
    }

    /**
    * Listen: register a callback for an event name or a wildcard pattern.
    * @param {string} listenerId
    * @param {string} pattern
    * @param {function} callback
    */
    function listen(listenerId, pattern, callback) {
        if (typeof listenerId !== 'string' || listenerId.trim() === '') {
            throw new Error("Listener ID must be a non-empty string.");
        }
        if (typeof pattern !== 'string' || pattern.trim() === '') {
            throw new Error("Event pattern must be a non-empty string.");
        }

        // Create a new listener entry
        LISTENERS.push({
            listenerId,
            pattern,
            callback
        });

        // Catch-up relevant events from the queue
        for (let i = EVENT_QUEUE.length - 1; i >= 0; i--) {
            let { throwerId, eventName, data } = EVENT_QUEUE[i];
            if (eventMatchesPattern(eventName, pattern)) {
                callback.call(this, throwerId, data, eventName);
                EVENT_QUEUE.splice(i, 1);
                console.log(`Event "${eventName}" caught up.`);
            }
        }
    }

    /**
    * Ignore: unregister a listener from a given pattern (or exact event).
    * @param {string} listenerId
    * @param {string} pattern
    */
    function ignore(listenerId, pattern) {
        if (typeof listenerId !== 'string' || listenerId.trim() === '') {
            throw new Error("Listener ID must be a non-empty string.");
        }
        if (typeof pattern !== 'string' || pattern.trim() === '') {
            throw new Error("Event pattern must be a non-empty string.");
        }

        // Filter out the matching listener(s)
        for (let i = LISTENERS.length - 1; i >= 0; i--) {
            const entry = LISTENERS[i];
            if (entry.listenerId === listenerId && entry.pattern === pattern) {
                LISTENERS.splice(i, 1);
            }
        }
    }

    /**
    * Helper: Does the eventName match a given pattern?
    * - If pattern has no special wildcard characters, it must match exactly.
    * - If pattern contains wildcard(s) like '*', we do a simple conversion to RegExp.
    *
    * @param {string} eventName
    * @param {string} pattern
    * @returns {boolean}
    */
    function eventMatchesPattern(eventName, pattern) {
        // Quick optimization if there's no wildcard in the pattern
        if (!pattern.includes('*')) {
            return (eventName === pattern);
        }

        // Convert the pattern to a RegExp: 
        // 1) Escape all regex meta-characters except `*`.  
        // 2) Replace `*` with `.*` 
        // 3) Anchor ^ and $
        const regexStr = '^' + pattern
            .replace(/[.+?^${}()|[\]\\]/g, '\\$&') // Escape everything except '*'
            .replace(/\*/g, '.*') + '$';

        const regex = new RegExp(regexStr);
        return regex.test(eventName);
    }

