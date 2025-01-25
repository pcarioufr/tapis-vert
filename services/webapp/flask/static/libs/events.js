// EVENTS ------ ------ ------ ------ ------ */

    // a library for event handling, through a sync event bus
    // the bus supports an events buffer for listeners 

    /**
    * Each listener is stored as an object:
    * {
    *   listenerId: string // an identifier for the listener - not necessarily unique across listeners
    *   pattern: string // the event name to match, can be exact name or pattern with wildcards
    *   callback: function that is called when a matching event is fired
    * }
    */
    const LISTENERS = [];


    /* The event history, for new listeners registered to catch up on past events. */
    const EVENT_HISTORY = [];
    const HISTORY_MAX_LENGTH = 100;

    /**
    * Fire: triggers any listener whose pattern matches the eventName.
    * @param {string} throwerId
    * @param {string} eventName
    * @param {*} data
    */
    function fire(throwerId, eventName, data) {

        // Create a new event object
        const event = { throwerId, eventName, data };
      
        // Updates event history
        EVENT_HISTORY.push(event);
        if (EVENT_HISTORY.length > HISTORY_MAX_LENGTH) { EVENT_HISTORY.shift(); }
      
        // Immediately dispatch to all *current* listeners
        for ( const { pattern, callback } of LISTENERS ) {
            if (eventMatchesPattern(eventName, pattern)) 
                callback(throwerId, data, eventName);
        }

      }

    /**
    * Listen: register a callback for an event name or a wildcard pattern.
    * @param {string} listenerId
    * @param {string} pattern
    * @param {function} callback
    * @param {bool} replay - whether to replay the event history on listener creation.
    * Beware, if the callback is async and/or if the callback itself fires events,
    * newly fired events might interleave with the replay and order is not guaranteed
    */
    function listen(listenerId, pattern, callback, replay = true) {
    
        LISTENERS.push({ listenerId, pattern, callback });

        if (replay) {
            const event_history_snapshot = EVENT_HISTORY.slice();
            for (const event of event_history_snapshot) {
                if (eventMatchesPattern(event.eventName, pattern)) {
                    callback(event.throwerId, event.data, event.eventName);
                    console.log(`Caught up on event: ${event.eventName}`);
                }
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
