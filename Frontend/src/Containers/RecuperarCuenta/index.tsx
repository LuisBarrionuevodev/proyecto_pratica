import { Box } from "@mui/material";
import { useState } from "react";
import Slide from "@mui/material/Slide";
import EmailBox from "./Components/EmailBox";
import CodigoBox from "./Components/CodigoBox";
import NuevaContraseña from "./Components/NuevaContraseña";

const RecuperarCuenta = () => {
    const [step, setStep] = useState<"email" | "codigo" | "contraseña">("email");
    const [email, setEmail] = useState("");

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
                    <NuevaContraseña/>
                </Box>
            </Slide>
        </Box>
    );
};

export default RecuperarCuenta;
