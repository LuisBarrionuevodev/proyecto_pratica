import type { JSX } from "react";
import { useEffect } from "react";
import LoginBox from "./Components/LoginBox";
import { Slide } from "@mui/material";
import { setBodyPublicRoute } from "../../theme/bodyRouteClass";
import { PublicAuthScreenLayout } from "../../components/auth/PublicAuthScreenLayout";

const Login = (): JSX.Element => {
    useEffect(() => {
        setBodyPublicRoute(true);
        return () => setBodyPublicRoute(false);
    }, []);

    return (
        <PublicAuthScreenLayout>
            <Slide
                direction="down"
                in={true}
                appear
                timeout={1000}
            >
                <div>
                    <LoginBox />
                </div>
            </Slide>
        </PublicAuthScreenLayout>
    )
}

export default Login;
