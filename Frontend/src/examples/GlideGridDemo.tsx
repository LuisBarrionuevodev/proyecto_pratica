/**
 * Componente de Demo para Glide Data Grid
 * 
 * Este componente muestra ejemplos de todas las capacidades de estilización
 * de Glide Data Grid, similar a la imagen de referencia.
 * 
 * Incluye:
 * - Badges con colores
 * - Gráficos sparkline
 * - Checkboxes
 * - Imágenes
 * - Links/URLs
 * - Diferentes tipos de celdas
 */

import { useCallback, useMemo, useRef } from "react";
import DataEditor, {
    type GridCell,
    GridCellKind,
    type GridColumn,
    type Item,
    type Theme,
} from "@glideapps/glide-data-grid";
import "@glideapps/glide-data-grid/dist/index.css";
import { Box, Typography } from "@mui/material";
import {
    badgeRenderer,
    createBadgeCell,
    sparklineRenderer,
    createSparklineCell,
    generateRandomSparklineData,
} from "../customRenderers";

// Datos de ejemplo (similar a la imagen que mostró el usuario)
interface EmployeeData {
    id: number;
    email: string;
    firstName: string;
    lastName: string;
    photo: string;
    optIn: boolean;
    title: string;
    info: string;
    performance: number[];
    manager: string;
    hired: string;
    level: number;
}

const DEMO_DATA: EmployeeData[] = [
    {
        id: 1,
        email: "conor.predovic@gmail.com",
        firstName: "Abbie",
        lastName: "Smith",
        photo: "https://i.pravatar.cc/150?img=1",
        optIn: false,
        title: "Corporate Markets Producer",
        info: "https://example.com",
        performance: generateRandomSparklineData(12),
        manager: "Richard Hane",
        hired: "Fri Sep 12 2025",
        level: 52,
    },
    {
        id: 2,
        email: "layne.prohaska25@gmail.com",
        firstName: "Annie",
        lastName: "Conn",
        photo: "https://i.pravatar.cc/150?img=2",
        optIn: true,
        title: "Dynamic Quality Coordinator",
        info: "https://example.com",
        performance: generateRandomSparklineData(12),
        manager: "Keenan Rath",
        hired: "Wed Oct 15 2025",
        level: 83,
    },
    {
        id: 3,
        email: "mathias83@gmail.com",
        firstName: "Lacy",
        lastName: "Hahn",
        photo: "https://i.pravatar.cc/150?img=3",
        optIn: false,
        title: "Senior Interactions Specialist",
        info: "https://example.com",
        performance: generateRandomSparklineData(12),
        manager: "Verna Graham",
        hired: "Wed Apr 09 2025",
        level: 97,
    },
    {
        id: 4,
        email: "vicente.watsica82@gmail.com",
        firstName: "Keegan",
        lastName: "Parker",
        photo: "https://i.pravatar.cc/150?img=4",
        optIn: false,
        title: "Lead Creative Strategist",
        info: "https://example.com",
        performance: generateRandomSparklineData(12),
        manager: "Jack Stehr",
        hired: "Sun Aug 10 2025",
        level: 65,
    },
    {
        id: 5,
        email: "nelle.hills97@yahoo.com",
        firstName: "Jordan",
        lastName: "Wiza",
        photo: "https://i.pravatar.cc/150?img=5",
        optIn: true,
        title: "Senior Accounts Coordinator",
        info: "https://example.com",
        performance: generateRandomSparklineData(12),
        manager: "Davion Hoppe",
        hired: "Fri Jul 25 2025",
        level: 70,
    },
];

const COLUMNS = [
    { id: "id", title: "ID", width: 60 },
    { id: "email", title: "Email", width: 200 },
    { id: "firstName", title: "First name", width: 120 },
    { id: "lastName", title: "Last name", width: 120 },
    { id: "photo", title: "Photo", width: 80 },
    { id: "optIn", title: "Opt-In", width: 80 },
    { id: "title", title: "Title", width: 220 },
    { id: "info", title: "More Info", width: 180 },
    { id: "performance", title: "Performance", width: 150 },
    { id: "manager", title: "Manager", width: 150 },
    { id: "hired", title: "Hired", width: 140 },
    { id: "level", title: "Level", width: 80 },
];

const GlideGridDemo = () => {
    const gridRef = useRef<any>(null);

    const columns = useMemo<GridColumn[]>(
        () =>
            COLUMNS.map((col) => ({
                title: col.title,
                id: col.id,
                width: col.width,
            })),
        []
    );

    const getCellContent = useCallback(([col, row]: Item): GridCell => {
        const rowData = DEMO_DATA[row];
        const columnId = COLUMNS[col].id;

        if (!rowData) {
            return {
                kind: GridCellKind.Text,
                data: "",
                displayData: "",
                allowOverlay: false,
            };
        }

        switch (columnId) {
            case "id":
                return {
                    kind: GridCellKind.Number,
                    data: rowData.id,
                    displayData: rowData.id.toString(),
                    allowOverlay: false,
                };

            case "email":
                return {
                    kind: GridCellKind.Text,
                    data: rowData.email,
                    displayData: rowData.email,
                    allowOverlay: true,
                };

            case "firstName":
                return {
                    kind: GridCellKind.Text,
                    data: rowData.firstName,
                    displayData: rowData.firstName,
                    allowOverlay: true,
                };

            case "lastName":
                return {
                    kind: GridCellKind.Text,
                    data: rowData.lastName,
                    displayData: rowData.lastName,
                    allowOverlay: true,
                };

            case "photo":
                return {
                    kind: GridCellKind.Image,
                    data: [rowData.photo],
                    displayData: [rowData.photo],
                    allowOverlay: false,
                    allowAdd: false,
                };

            case "optIn":
                return {
                    kind: GridCellKind.Boolean,
                    data: rowData.optIn,
                    allowOverlay: false,
                };

            case "title":
                return {
                    kind: GridCellKind.Text,
                    data: rowData.title,
                    displayData: rowData.title,
                    allowOverlay: true,
                };

            case "info":
                return {
                    kind: GridCellKind.Uri,
                    data: rowData.info,
                    displayData: rowData.info,
                    allowOverlay: false,
                    hoverEffect: true,
                };

            case "performance":
                return createSparklineCell(rowData.performance, "#ff6b6b", "area", false);

            case "manager":
                return createBadgeCell(rowData.manager, "info", "👤");

            case "hired":
                return {
                    kind: GridCellKind.Text,
                    data: rowData.hired,
                    displayData: rowData.hired,
                    allowOverlay: false,
                };

            case "level":
                // Color según el nivel
                let levelColor: "success" | "warning" | "error" = "success";
                if (rowData.level < 60) levelColor = "error";
                else if (rowData.level < 80) levelColor = "warning";

                return createBadgeCell(rowData.level.toString(), levelColor);

            default:
                return {
                    kind: GridCellKind.Text,
                    data: "",
                    displayData: "",
                    allowOverlay: false,
                };
        }
    }, []);

    const customTheme = useMemo<Partial<Theme>>(
        () => ({
            accentColor: "#4f46e5",
            accentLight: "#818cf8",
            textDark: "#1f2937",
            textMedium: "#6b7280",
            textLight: "#9ca3af",
            textBubble: "#ffffff",
            bgIconHeader: "#4f46e5",
            fgIconHeader: "#ffffff",
            textHeader: "#374151",
            textHeaderSelected: "#4f46e5",
            bgCell: "#ffffff",
            bgCellMedium: "#f9fafb",
            bgHeader: "#f3f4f6",
            bgHeaderHasFocus: "#e5e7eb",
            bgHeaderHovered: "#d1d5db",
            bgBubble: "#e5e7eb",
            bgBubbleSelected: "#4f46e5",
            bgSearchResult: "#fef3c7",
            borderColor: "#e5e7eb",
            drilldownBorder: "#4f46e5",
            linkColor: "#4f46e5",
            headerFontStyle: "600 14px",
            baseFontStyle: "13px",
            fontFamily:
                "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        }),
        []
    );

    return (
        <Box sx={{ p: 3 }}>
            <Typography variant="h4" sx={{ mb: 2, fontWeight: 600 }}>
                Glide Data Grid - Demo de Estilos Avanzados 🎨
            </Typography>
            <Typography variant="body1" sx={{ mb: 3, color: "text.secondary" }}>
                Este demo muestra todas las capacidades de estilización como en tu imagen de
                referencia: badges, gráficos sparkline, checkboxes, imágenes, links y más.
            </Typography>

            <Box
                sx={{
                    height: "600px",
                    border: "1px solid #e5e7eb",
                    borderRadius: "8px",
                    overflow: "hidden",
                    boxShadow: "0 4px 6px -1px rgba(0, 0, 0, 0.1)",
                }}
            >
                <DataEditor
                    ref={gridRef}
                    getCellContent={getCellContent}
                    columns={columns}
                    rows={DEMO_DATA.length}
                    theme={customTheme}
                    customRenderers={[badgeRenderer, sparklineRenderer]}
                    smoothScrollX={true}
                    smoothScrollY={true}
                    rowMarkers="both"
                    rowHeight={50}
                    headerHeight={44}
                    getCellsForSelection={true}
                    freezeColumns={1}
                />
            </Box>

            <Box sx={{ mt: 3, p: 2, bgcolor: "#f9fafb", borderRadius: "8px" }}>
                <Typography variant="h6" sx={{ mb: 1, fontWeight: 600 }}>
                    Características Mostradas:
                </Typography>
                <ul style={{ margin: 0, paddingLeft: "20px" }}>
                    <li>
                        <strong>Badges personalizados:</strong> Manager y Level con colores
                    </li>
                    <li>
                        <strong>Gráficos sparkline:</strong> Performance con área rellena
                    </li>
                    <li>
                        <strong>Checkboxes:</strong> Opt-In (clickeable)
                    </li>
                    <li>
                        <strong>Imágenes:</strong> Fotos de perfil
                    </li>
                    <li>
                        <strong>Links/URLs:</strong> More Info (clickeable)
                    </li>
                    <li>
                        <strong>Números:</strong> ID y Level
                    </li>
                    <li>
                        <strong>Texto editable:</strong> Email, First name, Last name, Title
                    </li>
                </ul>
            </Box>
        </Box>
    );
};

export default GlideGridDemo;
