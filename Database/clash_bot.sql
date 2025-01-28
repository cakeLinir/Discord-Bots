CREATE DATABASE  IF NOT EXISTS `clash_bot` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `clash_bot`;
-- MySQL dump 10.13  Distrib 8.0.40, for Win64 (x86_64)
--
-- Host: localhost    Database: clash_bot
-- ------------------------------------------------------
-- Server version	8.0.40

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `clanspiele`
--

DROP TABLE IF EXISTS `clanspiele`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `clanspiele` (
  `id` int NOT NULL AUTO_INCREMENT,
  `start_time` datetime NOT NULL,
  `end_time` datetime NOT NULL,
  `progress` int DEFAULT '0',
  `message_id` bigint DEFAULT NULL,
  `channel_id` bigint DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `sort_order` varchar(10) DEFAULT 'desc',
  `current_page` int DEFAULT '1',
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `clanspiele`
--

LOCK TABLES `clanspiele` WRITE;
/*!40000 ALTER TABLE `clanspiele` DISABLE KEYS */;
INSERT INTO `clanspiele` VALUES (3,'2025-01-22 00:00:00','2025-01-28 00:00:00',0,NULL,NULL,'2025-01-27 08:19:37','desc',1),(4,'2025-01-22 00:00:00','2025-01-28 00:00:00',0,NULL,NULL,'2025-01-27 08:20:28','desc',1),(5,'2025-01-22 00:00:00','2025-01-28 00:00:00',62850,1333398324413464658,1326612623642595399,'2025-01-27 08:20:48','desc',1);
/*!40000 ALTER TABLE `clanspiele` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `clanspiele_players`
--

DROP TABLE IF EXISTS `clanspiele_players`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `clanspiele_players` (
  `id` int NOT NULL AUTO_INCREMENT,
  `clanspiele_id` int NOT NULL,
  `player_tag` varchar(20) NOT NULL,
  `coc_name` varchar(50) NOT NULL,
  `discord_id` bigint DEFAULT NULL,
  `points` int DEFAULT '0',
  PRIMARY KEY (`id`),
  KEY `clanspiele_id` (`clanspiele_id`),
  CONSTRAINT `clanspiele_players_ibfk_1` FOREIGN KEY (`clanspiele_id`) REFERENCES `clanspiele` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=36 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `clanspiele_players`
--

LOCK TABLES `clanspiele_players` WRITE;
/*!40000 ALTER TABLE `clanspiele_players` DISABLE KEYS */;
INSERT INTO `clanspiele_players` VALUES (2,5,'#PU88990JQ','hundekuchenTTV',333006296611684352,4000),(3,5,'#LVCQGRY2C','salzpizza',NULL,4000),(4,5,'#L9CQ8RVP0','Mescher stark 3',NULL,1150),(5,5,'#CYJVUR9Q','schumi8',NULL,4000),(6,5,'#QQJ0QRYRG','qwertz',NULL,4000),(7,5,'#QJCV999PC','Jason007',NULL,2150),(8,5,'#QPY0GJ0L0','ficcccccccen',NULL,4000),(9,5,'#QUQYVU9QP','Julian 10',NULL,800),(10,5,'#QV9UGY98L','Gustav',NULL,4000),(11,5,'#Q2CRCUUQJ','CoC Basti',NULL,200),(12,5,'#YG0JVQYC','Eyleen',NULL,4000),(13,5,'#G890Y98PC','HandiH88',NULL,0),(14,5,'#GPJCRJQ0Q','gesiku',NULL,900),(15,5,'#LY890LV8R','lennart2',NULL,0),(16,5,'#LY890LV8R','lennart2',NULL,4000),(17,5,'#QJRVUG00R','moh(•—•)',NULL,0),(18,5,'#C0QGYYJ','Pielo',NULL,0),(19,5,'#QQVVGC9P2','shaggy',NULL,2250),(20,5,'#Q9PYVUGJL','Elek',NULL,150),(21,5,'#LYLCLGGC','HerkuGamer',NULL,300),(22,5,'#QVU2V0R2R','c.p.c',NULL,0),(23,5,'#G8QV9VJVU','Sebigboss',NULL,4000),(24,5,'#PUV8J9YGC','HORSCH112',NULL,200),(25,5,'#QLPC00Q8G','muhammed_19',NULL,500),(26,5,'#LCVQ9UJ02','moin',NULL,0),(27,5,'#LGLC0V0JQ','Paul f2p 2ac',NULL,0),(28,5,'#PPRCJGLPY','Blauubeere',NULL,0),(29,5,'#GP928PVRR','XOR',NULL,0),(30,5,'#GR90LV8UV','LordxShoota',NULL,0),(31,5,'#QLVR28JVG','Rooobert',NULL,2250),(32,5,'#GL8GL289Q','Herbert',NULL,4000),(33,5,'#PGQLGJ9J','Fleischkeule',NULL,4000),(34,5,'#G0JJ09QG8','-_-',NULL,4000),(35,5,'#G82LR0LLR','huhuhu',NULL,4000);
/*!40000 ALTER TABLE `clanspiele_players` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `event_channels`
--

DROP TABLE IF EXISTS `event_channels`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `event_channels` (
  `id` int NOT NULL AUTO_INCREMENT,
  `event_type` varchar(50) NOT NULL,
  `channel_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `event_type` (`event_type`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `event_channels`
--

LOCK TABLES `event_channels` WRITE;
/*!40000 ALTER TABLE `event_channels` DISABLE KEYS */;
INSERT INTO `event_channels` VALUES (1,'clanspiele',1326612623642595399);
/*!40000 ALTER TABLE `event_channels` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` int NOT NULL AUTO_INCREMENT,
  `discord_id` bigint DEFAULT NULL,
  `player_tag` varchar(20) NOT NULL,
  `role` varchar(20) DEFAULT NULL,
  `coc_name` varchar(50) NOT NULL,
  `warn_time` int DEFAULT '0',
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `player_tag` (`player_tag`)
) ENGINE=InnoDB AUTO_INCREMENT=49 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (1,333006296611684352,'#PU88990JQ','coLeader','hundekuchenTTV',0,'2025-01-25 17:14:09'),(2,NULL,'#CJ8YQY8Q',NULL,'Baltasar',0,'2025-01-25 17:14:40'),(3,NULL,'#G0JJ09QG8',NULL,'-_-',0,'2025-01-25 17:14:55'),(4,NULL,'#PGQLGJ9J',NULL,'Fleischkeule',0,'2025-01-25 17:15:08'),(5,NULL,'#RL9Q2VYQ',NULL,'TerorXD',0,'2025-01-25 17:15:51'),(6,NULL,'#GL8GL289Q',NULL,'Herbert',0,'2025-01-25 17:16:26'),(7,NULL,'#QLVR28JVG',NULL,'Rooobert',0,'2025-01-25 17:16:33'),(8,NULL,'#GR90LV8UV',NULL,'LordxShoota',0,'2025-01-25 17:16:45'),(9,NULL,'#PPRCJGLPY',NULL,'Blauubeere',0,'2025-01-25 17:17:00'),(10,NULL,'#GP928PVRR',NULL,'XOR',0,'2025-01-25 17:17:10'),(13,NULL,'#QLPC00Q8G',NULL,'muhammed_19',0,'2025-01-25 17:17:55'),(15,NULL,'#G8QV9VJVU',NULL,'Sebigboss',0,'2025-01-25 17:18:18'),(16,NULL,'#QVU2V0R2R',NULL,'c.p.c',0,'2025-01-25 17:18:43'),(19,NULL,'#QQVVGC9P2',NULL,'shaggy',0,'2025-01-25 17:19:09'),(20,NULL,'#C0QGYYJ',NULL,'Pielo',0,'2025-01-25 17:19:24'),(21,NULL,'#QJRVUG00R',NULL,'moh(•—•)',0,'2025-01-25 17:20:04'),(22,NULL,'#Q0JQYVL92',NULL,'iPhantoka',0,'2025-01-25 17:20:11'),(23,NULL,'#LY890LV8R',NULL,'lennart2',0,'2025-01-25 17:20:18'),(24,NULL,'#GPJCRJQ0Q',NULL,'gesiku',0,'2025-01-25 17:20:26'),(25,NULL,'#G890Y98PC',NULL,'HandiH88',0,'2025-01-25 17:20:34'),(26,NULL,'#YG0JVQYC',NULL,'Eyleen',0,'2025-01-25 17:20:56'),(27,NULL,'#Q2CRCUUQJ',NULL,'CoC Basti',0,'2025-01-25 17:21:01'),(28,NULL,'#QV9UGY98L',NULL,'Gustav',0,'2025-01-25 17:21:07'),(29,NULL,'#QUQYVU9QP',NULL,'Julian 10',0,'2025-01-25 17:21:24'),(30,NULL,'#QPY0GJ0L0',NULL,'ficcccccccen',0,'2025-01-25 17:21:35'),(31,NULL,'#QJCV999PC',NULL,'Jason007',0,'2025-01-25 17:21:56'),(32,NULL,'#QQJ0QRYRG',NULL,'qwertz',0,'2025-01-25 17:22:01'),(33,NULL,'#CYJVUR9Q',NULL,'schumi8',0,'2025-01-25 17:22:08'),(34,NULL,'#L9CQ8RVP0',NULL,'Mescher stark 3',0,'2025-01-25 17:22:17'),(35,NULL,'#LVCQGRY2C',NULL,'salzpizza',0,'2025-01-25 17:22:24'),(36,NULL,'#G82LR0LLR',NULL,'huhuhu',0,'2025-01-27 10:31:20'),(38,NULL,'#QQR9UULUV',NULL,'lacho',0,'2025-01-27 14:01:09'),(40,NULL,'#G02CYCLJR',NULL,'Wapiti',0,'2025-01-27 14:01:10'),(41,NULL,'#Q2VP9VU90',NULL,'hara ii',0,'2025-01-27 14:01:10'),(42,NULL,'#LVPQC2V0P',NULL,'juli',0,'2025-01-27 14:01:11'),(43,NULL,'#LCYJGP08G',NULL,'Blat',0,'2025-01-27 14:01:11'),(44,NULL,'#QRLQC20UQ',NULL,'AO_Leon',0,'2025-01-27 14:01:11'),(45,NULL,'#GPRL082CQ',NULL,'moody grunt',0,'2025-01-27 14:01:11'),(46,NULL,'#G8J0PRV22',NULL,'Luca[Donate]',0,'2025-01-27 14:01:12'),(47,NULL,'#22U2CQV2C',NULL,'Christoph',0,'2025-01-27 14:01:12'),(48,NULL,'#GQY8VR8VV',NULL,'GOTT',0,'2025-01-27 14:01:12');
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2025-01-28 15:26:13
