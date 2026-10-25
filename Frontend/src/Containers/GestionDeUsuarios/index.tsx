import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { fetchProfileMe } from "../../auth/profileMeSession";
import TableGestionDeUsuarios from "./Components/TableGestionDeUsuarios";

const GestionDeUsuarios = () => {
    const navigate = useNavigate();
    const [allowed, setAllowed] = useState<boolean | null>(null);

    useEffect(() => {
        const checkRole = async () => {
            try {
                const me = await fetchProfileMe();
                if (me.user.role !== "admin") {
                    navigate("/inicio", { replace: true });
                    setAllowed(false);
                    return;
                }
                setAllowed(true);
            } catch {
                navigate("/login", { replace: true });
                setAllowed(false);
            }
        };
        checkRole();
    }, [navigate]);

    if (allowed !== true) {
        return null;
    }

    return <TableGestionDeUsuarios />;
};

export default GestionDeUsuarios;