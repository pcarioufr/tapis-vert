    // TEST UTILS ------ ------ ------ ------ ------ */


    // A class utility to test API endpoints
    class Test {

        // test the auth endpoint
        static auth () {
            call('GET', '/api/auth/test')
        }

    }
