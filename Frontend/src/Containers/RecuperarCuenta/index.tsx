import { Box } from "@mui/material";
import { useState } from "react";
import Slide from "@mui/material/Slide";
import { useNavigate } from "react-router-dom";
import EmailBox from "./Components/EmailBox";
import CodigoBox from "./Components/CodigoBox";
import NuevaContraseña from "./Components/NuevaContraseña";

const RecuperarCuenta = () => {
    const navigate = useNavigate();
    const [step, setStep] = useState<"email" | "codigo" | "contraseña">("email");
    const [email, setEmail] = useState("");
    const [code, setCode] = useState("");

    return (
        <Box
            display="flex"
            justifyContent="center"
            alignItems="center"
            position="relative"
            width="100%"
            minHeight="500px"
        >
            <Slide
                direction="down"
                in={step === "email"}
                timeout={{ enter: 700, exit: 400 }}
                mountOnEnter
                unmountOnExit
            >
                <Box position="absolute">
                    <EmailBox
                        setEmailGlobal={setEmail}
                        onSuccess={() => setStep("codigo")}
                    />
                </Box>
            </Slide>

            <Slide
                direction="right"
                in={step === "codigo"}
                timeout={{ enter: 700, exit: 400 }}
                mountOnEnter
                unmountOnExit
            >
                <Box position="absolute">
                    <CodigoBox
                        email={email}
                        onCodeChange={setCode}
                        onSuccess={() => setStep("contraseña")}
                    />
                </Box>
            </Slide>

            <Slide
                direction="left"
                in={step === "contraseña"}
                timeout={{ enter: 700, exit: 400 }}
                mountOnEnter
                unmountOnExit
            >
                <Box position={"absolute"}>
                    <NuevaContraseña
                        email={email}
                        code={code}
                        onSuccess={() => navigate("/")}
                    />
                </Box>
            </Slide>
        </Box>
    );
};

export default RecuperarCuenta;
