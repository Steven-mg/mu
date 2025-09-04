-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Servidor: 127.0.0.1
-- Tiempo de generación: 04-09-2025 a las 15:40:59
-- Versión del servidor: 10.4.32-MariaDB
-- Versión de PHP: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Base de datos: `finca3`
--

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `actividad_reciente`
--

CREATE TABLE `actividad_reciente` (
  `id_actividad` int(11) NOT NULL,
  `usuario_id` int(11) NOT NULL,
  `accion` varchar(50) NOT NULL,
  `elemento` varchar(100) NOT NULL,
  `fecha` datetime NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `animal`
--

CREATE TABLE `animal` (
  `id_animal` smallint(6) NOT NULL,
  `nombre_animal` varchar(15) NOT NULL,
  `id_raza` tinyint(4) NOT NULL,
  `fecha_nacimiento` date NOT NULL,
  `sexo` varchar(6) NOT NULL,
  `id_finca` smallint(6) NOT NULL,
  `id_padre` smallint(6) DEFAULT NULL,
  `id_madre` smallint(6) DEFAULT NULL,
  `ubicacion_animal` enum('en finca','fuera de la finca','desconocido') NOT NULL,
  `origen` enum('nacido_en_finca','comprado','otro') DEFAULT 'otro',
  `id_estado_reprod` tinyint(4) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura Stand-in para la vista `animales_nacidos_finca`
-- (Véase abajo para la vista actual)
--
CREATE TABLE `animales_nacidos_finca` (
`id_animal` smallint(6)
,`nombre_animal` varchar(15)
,`id_raza` tinyint(4)
,`fecha_nacimiento` date
,`sexo` varchar(6)
,`id_finca` smallint(6)
,`id_padre` smallint(6)
,`id_madre` smallint(6)
,`ubicacion_animal` enum('en finca','fuera de la finca','desconocido')
,`origen` enum('nacido_en_finca','comprado','otro')
,`id_estado_reprod` tinyint(4)
,`nombre_padre` varchar(15)
,`nombre_madre` varchar(15)
);

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `animal_grupo`
--

CREATE TABLE `animal_grupo` (
  `id` int(11) NOT NULL,
  `id_animal` smallint(6) NOT NULL,
  `id_grupo` smallint(6) NOT NULL,
  `fecha_asignacion` date NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `ciclo_reproductivo`
--

CREATE TABLE `ciclo_reproductivo` (
  `id_ciclo` int(11) NOT NULL,
  `id_animal` smallint(6) NOT NULL,
  `fecha_inicio` date NOT NULL,
  `fecha_fin` date DEFAULT NULL,
  `tipo_ciclo` enum('celo','gestación','lactancia','descanso') NOT NULL,
  `duracion_esperada` int(11) DEFAULT NULL COMMENT 'Duración esperada en días',
  `notas` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `cria`
--

CREATE TABLE `cria` (
  `id_cria` smallint(6) NOT NULL,
  `id_padre` smallint(6) NOT NULL,
  `id_madre` smallint(6) NOT NULL,
  `id_animal` smallint(6) NOT NULL,
  `nombre_cria` varchar(30) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `estado_general`
--

CREATE TABLE `estado_general` (
  `id_estado` int(11) NOT NULL,
  `id_animal` smallint(6) NOT NULL,
  `estado` enum('vivo','muerto','vendido') DEFAULT NULL,
  `fecha_estado` date DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `estado_reproductivo`
--

CREATE TABLE `estado_reproductivo` (
  `id_estado_reprod` tinyint(4) NOT NULL,
  `descripcion` varchar(20) NOT NULL,
  `duracion_promedio` int(11) DEFAULT NULL COMMENT 'Duración promedio en días',
  `intervalo_entre_ciclos` int(11) DEFAULT NULL COMMENT 'Días entre ciclos'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `estado_salud`
--

CREATE TABLE `estado_salud` (
  `id_estado_salud` tinyint(4) NOT NULL,
  `descripcion` varchar(20) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `finca`
--

CREATE TABLE `finca` (
  `id_finca` smallint(6) NOT NULL,
  `nombre_finca` varchar(30) NOT NULL,
  `localizacion` varchar(100) DEFAULT NULL,
  `correo` varchar(60) NOT NULL,
  `telefono` varchar(15) DEFAULT NULL,
  `nombreEncargado` varchar(40) DEFAULT NULL,
  `pais` varchar(50) DEFAULT NULL,
  `departamento` varchar(50) DEFAULT NULL,
  `ciudad` varchar(50) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `grupo_animal`
--

CREATE TABLE `grupo_animal` (
  `id_grupo` smallint(6) NOT NULL,
  `id_finca` smallint(6) NOT NULL,
  `nombre_grupo` varchar(50) NOT NULL,
  `descripcion` text DEFAULT NULL,
  `fecha_creacion` date NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `historial_estado_reproductivo`
--

CREATE TABLE `historial_estado_reproductivo` (
  `id_historial_reprod` int(11) NOT NULL,
  `id_animal` smallint(6) NOT NULL,
  `id_estado_reprod` tinyint(4) NOT NULL,
  `fecha_cambio` datetime DEFAULT current_timestamp(),
  `observaciones` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `historial_estado_salud`
--

CREATE TABLE `historial_estado_salud` (
  `id_historial_salud` int(11) NOT NULL,
  `id_animal` smallint(6) NOT NULL,
  `id_estado_salud` tinyint(4) NOT NULL,
  `fecha_cambio` datetime DEFAULT current_timestamp(),
  `observaciones` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `madre`
--

CREATE TABLE `madre` (
  `id_madre` smallint(6) NOT NULL,
  `nombre_madre` varchar(30) DEFAULT NULL,
  `id_animal_madre` smallint(6) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `padre`
--

CREATE TABLE `padre` (
  `id_padre` smallint(6) NOT NULL,
  `nombre_padre` varchar(30) DEFAULT NULL,
  `id_animal_padre` smallint(6) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `potrero`
--

CREATE TABLE `potrero` (
  `id_potrero` smallint(6) NOT NULL,
  `id_finca` smallint(6) NOT NULL,
  `nombre_potrero` varchar(50) NOT NULL,
  `extension` decimal(10,2) NOT NULL COMMENT 'Extensión en hectáreas',
  `tipo_pasto` varchar(50) DEFAULT NULL,
  `fecha_ultima_rotacion` date DEFAULT NULL,
  `estado` enum('activo','descanso','mantenimiento') NOT NULL DEFAULT 'activo',
  `capacidad_animal` smallint(6) DEFAULT NULL COMMENT 'Cantidad de animales recomendada',
  `notas` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `productos`
--

CREATE TABLE `productos` (
  `id_producto` tinyint(4) NOT NULL,
  `nombre_producto` varchar(20) NOT NULL,
  `descripcion_producto` varchar(300) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `productos_animal`
--

CREATE TABLE `productos_animal` (
  `id_produccion` mediumint(9) NOT NULL,
  `id_producto` tinyint(4) NOT NULL,
  `id_animal` smallint(6) NOT NULL,
  `cantidad` float NOT NULL,
  `fecha` date NOT NULL,
  `notas_produccion` varchar(250) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `raza`
--

CREATE TABLE `raza` (
  `id_raza` tinyint(4) NOT NULL,
  `nombre_raza` varchar(30) NOT NULL,
  `produccion_leche_aprox` float NOT NULL,
  `peso_nacimiento` float DEFAULT NULL,
  `edad_madurez` tinyint(4) DEFAULT NULL,
  `tipo_raza` varchar(20) NOT NULL,
  `expectativa_vida` tinyint(4) NOT NULL,
  `adaptabilidad_clima` varchar(20) NOT NULL,
  `notas` varchar(250) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `registro_peso`
--

CREATE TABLE `registro_peso` (
  `id_registro` int(11) NOT NULL,
  `id_animal` smallint(6) NOT NULL,
  `fecha_registro` date NOT NULL,
  `peso` float NOT NULL COMMENT 'Peso en kg',
  `tipo_momento` enum('nacimieto','destete','mensual','preparto','postparto','engorde','control sanitario') NOT NULL DEFAULT 'mensual',
  `notas` varchar(250) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `reporte`
--

CREATE TABLE `reporte` (
  `id_reporte` int(11) NOT NULL,
  `titulo` varchar(100) NOT NULL,
  `descripcion` text DEFAULT NULL,
  `fecha_generacion` datetime NOT NULL DEFAULT current_timestamp(),
  `tipo_reporte` enum('ganado','produccion','salud','financiero','general') NOT NULL,
  `formato` enum('pdf','excel','csv','html') NOT NULL DEFAULT 'pdf',
  `usuario_id` int(11) NOT NULL,
  `finca_id` smallint(6) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `rotacion_potrero`
--

CREATE TABLE `rotacion_potrero` (
  `id_rotacion` int(11) NOT NULL,
  `id_potrero` smallint(6) NOT NULL,
  `fecha_inicio` date NOT NULL,
  `fecha_fin` date DEFAULT NULL,
  `tipo_uso` enum('pastoreo','descanso','siembra','fertilización','mantenimiento') NOT NULL,
  `id_grupo_animal` smallint(6) DEFAULT NULL COMMENT 'Grupo de animales asignado',
  `observaciones` text DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `servicios_salud`
--

CREATE TABLE `servicios_salud` (
  `id_servicio_salud` int(11) NOT NULL,
  `id_animal` smallint(6) NOT NULL,
  `id_tipo_salud` tinyint(4) NOT NULL,
  `id_veterinario` tinyint(4) NOT NULL,
  `fecha_servicio` date NOT NULL,
  `fecha_proximo` date DEFAULT NULL COMMENT 'Próxima fecha recomendada',
  `dosis` varchar(50) DEFAULT NULL,
  `observaciones` text DEFAULT NULL,
  `costo` decimal(8,2) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `servicios_sexuales`
--

CREATE TABLE `servicios_sexuales` (
  `id_servicios` smallint(6) NOT NULL,
  `id_servicioanimal` tinyint(4) NOT NULL,
  `id_animal` smallint(6) NOT NULL,
  `id_veterinario` tinyint(4) NOT NULL,
  `fecha_servicio` date NOT NULL,
  `notas_servicio` varchar(200) DEFAULT NULL,
  `costo_total` float DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `tipo_servicio_salud`
--

CREATE TABLE `tipo_servicio_salud` (
  `id_tipo_salud` tinyint(4) NOT NULL,
  `nombre_servicio` varchar(50) NOT NULL,
  `descripcion` text DEFAULT NULL,
  `categoria` enum('Vacunación','Desparasitación','Tratamiento médico','Suplemento','Cirugía','Control preventivo') NOT NULL,
  `frecuencia_recomendada` varchar(30) DEFAULT NULL COMMENT 'Ej: Anual, Trimestral, Única',
  `costo_referencia` decimal(8,2) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `tipo_servicio_sexual`
--

CREATE TABLE `tipo_servicio_sexual` (
  `id_servicio` smallint(6) NOT NULL,
  `nombre_servicio` varchar(20) NOT NULL,
  `descripcion_servicio` varchar(200) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `usuario`
--

CREATE TABLE `usuario` (
  `id` int(11) NOT NULL,
  `nik_name` varchar(50) NOT NULL,
  `nombres` varchar(50) DEFAULT NULL,
  `apellidos` varchar(50) DEFAULT NULL,
  `direccion` varchar(30) DEFAULT NULL,
  `telefono` varchar(15) DEFAULT NULL,
  `correo` varchar(120) NOT NULL,
  `contraseña` varchar(255) DEFAULT NULL,
  `tipo_usuario` tinyint(4) NOT NULL,
  `pais` varchar(50) DEFAULT NULL,
  `departamento` varchar(50) DEFAULT NULL,
  `ciudad` varchar(50) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `usuario`
--

INSERT INTO `usuario` (`id`, `nik_name`, `nombres`, `apellidos`, `direccion`, `telefono`, `correo`, `contraseña`, `tipo_usuario`, `pais`, `departamento`, `ciudad`) VALUES
(2, 'superadmin', NULL, NULL, 'Dirección Central', '987654321', 'superadmin@ganacontrol.com', '$2b$12$X6yKe9JD0k0yc64iKd.wGexdVnxf.23rpmPomyJw519yUlKwamBIW', 3, NULL, NULL, NULL),
(3, 'nombre_usuario', NULL, NULL, 'Dirección por defecto', 'Sin teléfono', 'correo@ejemplo.com', '$2b$12$fqeekcB9uvWPUqeFGD7HuegLcbZvb8bCRZa0IBbJQbaku7zw3bGn.', 2, NULL, NULL, NULL),
(6, 'lizard', 'lizeth', 'poveda', 'sdfs', '1234566', 'qq@gmail.com', '$2b$12$G2wumPf2nhRTdcZjsmj/c.hbnRuDHwzwiOibyFKn7LjhXOdTW5TgC', 2, 'Colombia', 'santander', 'Puente Nacional');

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `usuario_finca`
--

CREATE TABLE `usuario_finca` (
  `id` int(11) NOT NULL,
  `usuario_id` int(11) NOT NULL,
  `finca_id` smallint(6) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `veterinario`
--

CREATE TABLE `veterinario` (
  `id_veterinario` tinyint(4) NOT NULL,
  `nombre_veterinario` varchar(50) NOT NULL,
  `telefono` varchar(12) NOT NULL,
  `correo` varchar(40) NOT NULL,
  `direccion` varchar(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estructura para la vista `animales_nacidos_finca`
--
DROP TABLE IF EXISTS `animales_nacidos_finca`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `animales_nacidos_finca`  AS SELECT `a`.`id_animal` AS `id_animal`, `a`.`nombre_animal` AS `nombre_animal`, `a`.`id_raza` AS `id_raza`, `a`.`fecha_nacimiento` AS `fecha_nacimiento`, `a`.`sexo` AS `sexo`, `a`.`id_finca` AS `id_finca`, `a`.`id_padre` AS `id_padre`, `a`.`id_madre` AS `id_madre`, `a`.`ubicacion_animal` AS `ubicacion_animal`, `a`.`origen` AS `origen`, `a`.`id_estado_reprod` AS `id_estado_reprod`, `p`.`nombre_animal` AS `nombre_padre`, `m`.`nombre_animal` AS `nombre_madre` FROM ((`animal` `a` left join `animal` `p` on(`a`.`id_padre` = `p`.`id_animal`)) left join `animal` `m` on(`a`.`id_madre` = `m`.`id_animal`)) WHERE `a`.`origen` = 'nacido_en_finca' ;

--
-- Índices para tablas volcadas
--

--
-- Indices de la tabla `actividad_reciente`
--
ALTER TABLE `actividad_reciente`
  ADD PRIMARY KEY (`id_actividad`),
  ADD KEY `usuario_id` (`usuario_id`);

--
-- Indices de la tabla `animal`
--
ALTER TABLE `animal`
  ADD PRIMARY KEY (`id_animal`),
  ADD KEY `padre` (`id_padre`),
  ADD KEY `madre` (`id_madre`),
  ADD KEY `id_raza` (`id_raza`),
  ADD KEY `FK_idanimal` (`id_finca`),
  ADD KEY `id_estado_reprod` (`id_estado_reprod`);

--
-- Indices de la tabla `animal_grupo`
--
ALTER TABLE `animal_grupo`
  ADD PRIMARY KEY (`id`),
  ADD KEY `fk_animalgrupo_animal` (`id_animal`),
  ADD KEY `fk_animalgrupo_grupo` (`id_grupo`);

--
-- Indices de la tabla `ciclo_reproductivo`
--
ALTER TABLE `ciclo_reproductivo`
  ADD PRIMARY KEY (`id_ciclo`),
  ADD KEY `id_animal` (`id_animal`);

--
-- Indices de la tabla `cria`
--
ALTER TABLE `cria`
  ADD PRIMARY KEY (`id_cria`),
  ADD KEY `id_padre` (`id_padre`),
  ADD KEY `id_madre` (`id_madre`),
  ADD KEY `id_animal` (`id_animal`);

--
-- Indices de la tabla `estado_general`
--
ALTER TABLE `estado_general`
  ADD PRIMARY KEY (`id_estado`),
  ADD KEY `fk_estado_general_animal` (`id_animal`);

--
-- Indices de la tabla `estado_reproductivo`
--
ALTER TABLE `estado_reproductivo`
  ADD PRIMARY KEY (`id_estado_reprod`);

--
-- Indices de la tabla `estado_salud`
--
ALTER TABLE `estado_salud`
  ADD PRIMARY KEY (`id_estado_salud`);

--
-- Indices de la tabla `finca`
--
ALTER TABLE `finca`
  ADD PRIMARY KEY (`id_finca`);

--
-- Indices de la tabla `grupo_animal`
--
ALTER TABLE `grupo_animal`
  ADD PRIMARY KEY (`id_grupo`),
  ADD KEY `fk_grupo_finca` (`id_finca`);

--
-- Indices de la tabla `historial_estado_reproductivo`
--
ALTER TABLE `historial_estado_reproductivo`
  ADD PRIMARY KEY (`id_historial_reprod`),
  ADD KEY `id_animal` (`id_animal`),
  ADD KEY `id_estado_reprod` (`id_estado_reprod`);

--
-- Indices de la tabla `historial_estado_salud`
--
ALTER TABLE `historial_estado_salud`
  ADD PRIMARY KEY (`id_historial_salud`),
  ADD KEY `id_animal` (`id_animal`),
  ADD KEY `id_estado_salud` (`id_estado_salud`);

--
-- Indices de la tabla `madre`
--
ALTER TABLE `madre`
  ADD PRIMARY KEY (`id_madre`),
  ADD KEY `id_animal_madre` (`id_animal_madre`);

--
-- Indices de la tabla `padre`
--
ALTER TABLE `padre`
  ADD PRIMARY KEY (`id_padre`),
  ADD KEY `id_animal_padre` (`id_animal_padre`);

--
-- Indices de la tabla `potrero`
--
ALTER TABLE `potrero`
  ADD PRIMARY KEY (`id_potrero`),
  ADD KEY `fk_potrero_finca` (`id_finca`);

--
-- Indices de la tabla `productos`
--
ALTER TABLE `productos`
  ADD PRIMARY KEY (`id_producto`);

--
-- Indices de la tabla `productos_animal`
--
ALTER TABLE `productos_animal`
  ADD PRIMARY KEY (`id_produccion`),
  ADD KEY `id_producto` (`id_producto`),
  ADD KEY `id_animal` (`id_animal`);

--
-- Indices de la tabla `raza`
--
ALTER TABLE `raza`
  ADD PRIMARY KEY (`id_raza`);

--
-- Indices de la tabla `registro_peso`
--
ALTER TABLE `registro_peso`
  ADD PRIMARY KEY (`id_registro`),
  ADD KEY `id_animal` (`id_animal`);

--
-- Indices de la tabla `reporte`
--
ALTER TABLE `reporte`
  ADD PRIMARY KEY (`id_reporte`),
  ADD KEY `fk_reporte_usuario` (`usuario_id`),
  ADD KEY `fk_reporte_finca` (`finca_id`);

--
-- Indices de la tabla `rotacion_potrero`
--
ALTER TABLE `rotacion_potrero`
  ADD PRIMARY KEY (`id_rotacion`),
  ADD KEY `fk_rotacion_potrero` (`id_potrero`);

--
-- Indices de la tabla `servicios_salud`
--
ALTER TABLE `servicios_salud`
  ADD PRIMARY KEY (`id_servicio_salud`),
  ADD KEY `id_animal` (`id_animal`),
  ADD KEY `id_tipo_salud` (`id_tipo_salud`),
  ADD KEY `id_veterinario` (`id_veterinario`);

--
-- Indices de la tabla `servicios_sexuales`
--
ALTER TABLE `servicios_sexuales`
  ADD PRIMARY KEY (`id_servicioanimal`),
  ADD KEY `id_animal` (`id_animal`),
  ADD KEY `id_servicio` (`id_servicios`) USING BTREE,
  ADD KEY `Fk_veterinario` (`id_veterinario`);

--
-- Indices de la tabla `tipo_servicio_salud`
--
ALTER TABLE `tipo_servicio_salud`
  ADD PRIMARY KEY (`id_tipo_salud`);

--
-- Indices de la tabla `tipo_servicio_sexual`
--
ALTER TABLE `tipo_servicio_sexual`
  ADD PRIMARY KEY (`id_servicio`);

--
-- Indices de la tabla `usuario`
--
ALTER TABLE `usuario`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `nombre_usuario_UNIQUE` (`nik_name`),
  ADD UNIQUE KEY `correo_UNIQUE` (`correo`);

--
-- Indices de la tabla `usuario_finca`
--
ALTER TABLE `usuario_finca`
  ADD PRIMARY KEY (`id`),
  ADD KEY `id_usuario` (`usuario_id`),
  ADD KEY `id_finca` (`finca_id`);

--
-- Indices de la tabla `veterinario`
--
ALTER TABLE `veterinario`
  ADD PRIMARY KEY (`id_veterinario`);

--
-- AUTO_INCREMENT de las tablas volcadas
--

--
-- AUTO_INCREMENT de la tabla `actividad_reciente`
--
ALTER TABLE `actividad_reciente`
  MODIFY `id_actividad` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `animal`
--
ALTER TABLE `animal`
  MODIFY `id_animal` smallint(6) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `animal_grupo`
--
ALTER TABLE `animal_grupo`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `ciclo_reproductivo`
--
ALTER TABLE `ciclo_reproductivo`
  MODIFY `id_ciclo` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `cria`
--
ALTER TABLE `cria`
  MODIFY `id_cria` smallint(6) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `estado_general`
--
ALTER TABLE `estado_general`
  MODIFY `id_estado` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `estado_reproductivo`
--
ALTER TABLE `estado_reproductivo`
  MODIFY `id_estado_reprod` tinyint(4) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `estado_salud`
--
ALTER TABLE `estado_salud`
  MODIFY `id_estado_salud` tinyint(4) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `finca`
--
ALTER TABLE `finca`
  MODIFY `id_finca` smallint(6) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `grupo_animal`
--
ALTER TABLE `grupo_animal`
  MODIFY `id_grupo` smallint(6) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `historial_estado_reproductivo`
--
ALTER TABLE `historial_estado_reproductivo`
  MODIFY `id_historial_reprod` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `historial_estado_salud`
--
ALTER TABLE `historial_estado_salud`
  MODIFY `id_historial_salud` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `madre`
--
ALTER TABLE `madre`
  MODIFY `id_madre` smallint(6) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `padre`
--
ALTER TABLE `padre`
  MODIFY `id_padre` smallint(6) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `potrero`
--
ALTER TABLE `potrero`
  MODIFY `id_potrero` smallint(6) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `productos`
--
ALTER TABLE `productos`
  MODIFY `id_producto` tinyint(4) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `productos_animal`
--
ALTER TABLE `productos_animal`
  MODIFY `id_produccion` mediumint(9) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `raza`
--
ALTER TABLE `raza`
  MODIFY `id_raza` tinyint(4) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `registro_peso`
--
ALTER TABLE `registro_peso`
  MODIFY `id_registro` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `reporte`
--
ALTER TABLE `reporte`
  MODIFY `id_reporte` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `rotacion_potrero`
--
ALTER TABLE `rotacion_potrero`
  MODIFY `id_rotacion` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `servicios_salud`
--
ALTER TABLE `servicios_salud`
  MODIFY `id_servicio_salud` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `servicios_sexuales`
--
ALTER TABLE `servicios_sexuales`
  MODIFY `id_servicioanimal` tinyint(4) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `tipo_servicio_salud`
--
ALTER TABLE `tipo_servicio_salud`
  MODIFY `id_tipo_salud` tinyint(4) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `tipo_servicio_sexual`
--
ALTER TABLE `tipo_servicio_sexual`
  MODIFY `id_servicio` smallint(6) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `usuario`
--
ALTER TABLE `usuario`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- AUTO_INCREMENT de la tabla `usuario_finca`
--
ALTER TABLE `usuario_finca`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de la tabla `veterinario`
--
ALTER TABLE `veterinario`
  MODIFY `id_veterinario` tinyint(4) NOT NULL AUTO_INCREMENT;

--
-- Restricciones para tablas volcadas
--

--
-- Filtros para la tabla `actividad_reciente`
--
ALTER TABLE `actividad_reciente`
  ADD CONSTRAINT `actividad_reciente_ibfk_1` FOREIGN KEY (`usuario_id`) REFERENCES `usuario` (`id`);

--
-- Filtros para la tabla `animal`
--
ALTER TABLE `animal`
  ADD CONSTRAINT `FK_idanimal` FOREIGN KEY (`id_finca`) REFERENCES `finca` (`id_finca`),
  ADD CONSTRAINT `animal_ibfk_3` FOREIGN KEY (`id_raza`) REFERENCES `raza` (`id_raza`),
  ADD CONSTRAINT `fk_animal_madre_self` FOREIGN KEY (`id_madre`) REFERENCES `animal` (`id_animal`);

--
-- Filtros para la tabla `animal_grupo`
--
ALTER TABLE `animal_grupo`
  ADD CONSTRAINT `fk_animalgrupo_animal` FOREIGN KEY (`id_animal`) REFERENCES `animal` (`id_animal`) ON DELETE CASCADE,
  ADD CONSTRAINT `fk_animalgrupo_grupo` FOREIGN KEY (`id_grupo`) REFERENCES `grupo_animal` (`id_grupo`) ON DELETE CASCADE;

--
-- Filtros para la tabla `ciclo_reproductivo`
--
ALTER TABLE `ciclo_reproductivo`
  ADD CONSTRAINT `ciclo_reproductivo_ibfk_1` FOREIGN KEY (`id_animal`) REFERENCES `animal` (`id_animal`);

--
-- Filtros para la tabla `cria`
--
ALTER TABLE `cria`
  ADD CONSTRAINT `cria_ibfk_1` FOREIGN KEY (`id_padre`) REFERENCES `padre` (`id_padre`),
  ADD CONSTRAINT `cria_ibfk_2` FOREIGN KEY (`id_madre`) REFERENCES `madre` (`id_madre`),
  ADD CONSTRAINT `cria_ibfk_3` FOREIGN KEY (`id_animal`) REFERENCES `animal` (`id_animal`);

--
-- Filtros para la tabla `estado_general`
--
ALTER TABLE `estado_general`
  ADD CONSTRAINT `fk_estado_general_animal` FOREIGN KEY (`id_animal`) REFERENCES `animal` (`id_animal`);

--
-- Filtros para la tabla `grupo_animal`
--
ALTER TABLE `grupo_animal`
  ADD CONSTRAINT `fk_grupo_finca` FOREIGN KEY (`id_finca`) REFERENCES `finca` (`id_finca`) ON DELETE CASCADE;

--
-- Filtros para la tabla `historial_estado_reproductivo`
--
ALTER TABLE `historial_estado_reproductivo`
  ADD CONSTRAINT `historial_estado_reproductivo_ibfk_1` FOREIGN KEY (`id_animal`) REFERENCES `animal` (`id_animal`),
  ADD CONSTRAINT `historial_estado_reproductivo_ibfk_2` FOREIGN KEY (`id_estado_reprod`) REFERENCES `estado_reproductivo` (`id_estado_reprod`);

--
-- Filtros para la tabla `historial_estado_salud`
--
ALTER TABLE `historial_estado_salud`
  ADD CONSTRAINT `historial_estado_salud_ibfk_1` FOREIGN KEY (`id_animal`) REFERENCES `animal` (`id_animal`),
  ADD CONSTRAINT `historial_estado_salud_ibfk_2` FOREIGN KEY (`id_estado_salud`) REFERENCES `estado_salud` (`id_estado_salud`);

--
-- Filtros para la tabla `madre`
--
ALTER TABLE `madre`
  ADD CONSTRAINT `madre_ibfk_1` FOREIGN KEY (`id_animal_madre`) REFERENCES `animal` (`id_animal`);

--
-- Filtros para la tabla `padre`
--
ALTER TABLE `padre`
  ADD CONSTRAINT `padre_ibfk_1` FOREIGN KEY (`id_animal_padre`) REFERENCES `animal` (`id_animal`);

--
-- Filtros para la tabla `potrero`
--
ALTER TABLE `potrero`
  ADD CONSTRAINT `fk_potrero_finca` FOREIGN KEY (`id_finca`) REFERENCES `finca` (`id_finca`) ON DELETE CASCADE;

--
-- Filtros para la tabla `productos_animal`
--
ALTER TABLE `productos_animal`
  ADD CONSTRAINT `productos_animal_ibfk_1` FOREIGN KEY (`id_producto`) REFERENCES `productos` (`id_producto`),
  ADD CONSTRAINT `productos_animal_ibfk_2` FOREIGN KEY (`id_animal`) REFERENCES `animal` (`id_animal`);

--
-- Filtros para la tabla `registro_peso`
--
ALTER TABLE `registro_peso`
  ADD CONSTRAINT `registro_peso_ibfk_1` FOREIGN KEY (`id_animal`) REFERENCES `animal` (`id_animal`);

--
-- Filtros para la tabla `reporte`
--
ALTER TABLE `reporte`
  ADD CONSTRAINT `fk_reporte_finca` FOREIGN KEY (`finca_id`) REFERENCES `finca` (`id_finca`),
  ADD CONSTRAINT `fk_reporte_usuario` FOREIGN KEY (`usuario_id`) REFERENCES `usuario` (`id`);

--
-- Filtros para la tabla `rotacion_potrero`
--
ALTER TABLE `rotacion_potrero`
  ADD CONSTRAINT `fk_rotacion_potrero` FOREIGN KEY (`id_potrero`) REFERENCES `potrero` (`id_potrero`) ON DELETE CASCADE;

--
-- Filtros para la tabla `servicios_salud`
--
ALTER TABLE `servicios_salud`
  ADD CONSTRAINT `servicios_salud_ibfk_1` FOREIGN KEY (`id_animal`) REFERENCES `animal` (`id_animal`),
  ADD CONSTRAINT `servicios_salud_ibfk_2` FOREIGN KEY (`id_tipo_salud`) REFERENCES `tipo_servicio_salud` (`id_tipo_salud`),
  ADD CONSTRAINT `servicios_salud_ibfk_3` FOREIGN KEY (`id_veterinario`) REFERENCES `veterinario` (`id_veterinario`);

--
-- Filtros para la tabla `servicios_sexuales`
--
ALTER TABLE `servicios_sexuales`
  ADD CONSTRAINT `Fk_veterinario` FOREIGN KEY (`id_veterinario`) REFERENCES `veterinario` (`id_veterinario`),
  ADD CONSTRAINT `servicios_sexuales_ibfk_1` FOREIGN KEY (`id_servicios`) REFERENCES `tipo_servicio_sexual` (`id_servicio`),
  ADD CONSTRAINT `servicios_sexuales_ibfk_2` FOREIGN KEY (`id_animal`) REFERENCES `animal` (`id_animal`);

--
-- Filtros para la tabla `usuario_finca`
--
ALTER TABLE `usuario_finca`
  ADD CONSTRAINT `fk_usuario_finca_finca` FOREIGN KEY (`finca_id`) REFERENCES `finca` (`id_finca`),
  ADD CONSTRAINT `fk_usuario_finca_usuario` FOREIGN KEY (`usuario_id`) REFERENCES `usuario` (`id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
