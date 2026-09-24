import type { JSX } from "react";
import LoginBox from "./Components/LoginBox";
import { Box, Slide } from "@mui/material";

const Login = (): JSX.Element => {
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