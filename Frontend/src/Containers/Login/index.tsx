import type { JSX } from "react";
import { useEffect } from "react";
import LoginBox from "./Components/LoginBox";
import { Box, Slide } from "@mui/material";
import { setBodyPublicRoute } from "../../theme/bodyRouteClass";

const Login = (): JSX.Element => {
    useEffect(() => {
        setBodyPublicRoute(true);
        return () => setBodyPublicRoute(false);
    }, []);

    return (
        <Box
            display="flex"
            justifyContent="center"
            alignItems="center"
            minHeight="100vh"
        >
            <Slide
                direction="down"
                in={true}
                appear
                timeout={1000}
            >
                <Box>
                    <LoginBox />
                </Box>
            </Slide>
        </Box>
    )
}

export default Login;