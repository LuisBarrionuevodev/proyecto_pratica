import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient } from "../../api/apiClient";
import TableGestionDeUsuarios from "./Components/TableGestionDeUsuarios";

type MeResponse = {
    user: {
        role: "admin" | "usuario";
    };
};

const GestionDeUsuarios = () => {
    const navigate = useNavigate();
    const [allowed, setAllowed] = useState<boolean | null>(null);

    useEffect(() => {
        const checkRole = async () => {
            try {
                const res = await apiClient.get<MeResponse>("/api/profile/me");
                if (res.data.user.role !== "admin") {
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