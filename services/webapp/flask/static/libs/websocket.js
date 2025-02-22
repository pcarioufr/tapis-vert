    // WEBSOCKETS ------ ------ ------ ------ ------ */

    class EventWebSocket extends WebSocket {


        constructor(wsurl) {

            super(wsurl);  // Call the WebSocket constructor
            this.wsurl = wsurl;

            this.delay = 5000; // Delay before reconnecting

            this.onmessage = (event) => {
                let [key, value] = event.data.split('::', 2);
                try { value = JSON.parse(value); } 
                catch (e) { /* If not JSON, just use raw value */ }
                fire("websocket", key, value);
            };

            this.onopen = _ => {
                console.log("WebSocket connection established");
            };

            this.onclose = event => {
                new Toast("error", "Lost connection with room.", "wifi-off-line", this.delay - 1000);
                this.tryReconnect();
            };

        }

        // this.send(), but waiting for the websocket connection to open.
        // key will be prefixed by user:{{user.id}}: by the server
        async send(key, value, timeout = 5000) {

            const startTime = Date.now();

            const trySend = _ => {
                if (this.readyState === 1) {  // Check if WebSocket is open
                    super.send(`${key}::${value}`);
                    return true; // Successfully sent
                }
                return false; // Not ready
            };

            while (!trySend()) {
                if (Date.now() - startTime > timeout) {
                    console.error("WebSocket connection timed out");
                    return; // Exit the function after a timeout
                }
                await wait(5); // Pause for 5ms before retrying
            }
        }

        async tryReconnect() {

            await wait(this.delay);

            const newWs = new EventWebSocket(this.wsurl);
            newWs.onopen = _ => {
                new Toast("ok", "Recovered connection with room.", "wifi-line");
                Object.assign(this, newWs);
                fire ("EventWebSocket", "ws:reconnected", newWs);
            };

        }

    }
