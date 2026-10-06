BEGIN TRANSACTION;
CREATE TABLE admins (
	id INTEGER NOT NULL, 
	username VARCHAR(64) NOT NULL, 
	email VARCHAR(120) NOT NULL, 
	password_hash VARCHAR(256) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, failed_login_attempts INTEGER DEFAULT 0, locked_until DATETIME, totp_secret VARCHAR(64), is_2fa_enabled BOOLEAN DEFAULT 0, 
	PRIMARY KEY (id)
);
INSERT INTO "admins" VALUES(1,'store_owner','owner@scentedbubbles.com','scrypt:32768:8:1$nLqevEkk43WO23at$282673b41a5712910da52f318e3c5aba7fbb1d376be977948ecd9a49f356f63d87900bacd39650ff2ae379ed1af88b934632f797e5b5916604d255b24ffd18c6',1,'2026-09-30 17:44:30.471822','2026-09-30 17:44:30.471826',0,NULL,NULL,0);
INSERT INTO "admins" VALUES(2,'admin','admin@scentedbubbles.com','scrypt:32768:8:1$nEonEiEfbZa6gyhV$ddc3020b01c9c62178ca3af237cf38a8f6a6dfb9068e612c9e149c77dd74def56c3f72970ed74b4f9a79d3b34a2dddd8b78c5a17bcf0fdc367baf5de5bec4cdf',1,'2026-10-01 07:05:50.808344','2026-10-01 07:05:50.808349',0,NULL,NULL,0);
CREATE TABLE banners (
	id INTEGER NOT NULL, 
	title VARCHAR(150) NOT NULL, 
	subtitle VARCHAR(255), 
	link_url VARCHAR(255), 
	image_key VARCHAR(255) NOT NULL, 
	display_order INTEGER NOT NULL, 
	active BOOLEAN NOT NULL, 
	is_deleted BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, tagline VARCHAR(150), button_text VARCHAR(80) DEFAULT NULL, secondary_button_text VARCHAR(80), secondary_button_link VARCHAR(255), target_type VARCHAR(30) DEFAULT NULL, target_id INTEGER, overlay_opacity INTEGER DEFAULT 55, 
	PRIMARY KEY (id)
);
INSERT INTO "banners" VALUES(1,'Buy Any 3 Perfumes @ ₹1,099','Handcrafted Eau de Parfums inspired by iconic fragrances. Free luxury velvet pouch included.','/combos/prestige-quad-collection-offer','banner_20261004_153935_hero_banner_f449de_medium.webp',1,1,0,'2026-09-30 14:16:37.381859','','SHOP COMBO NOW','EXPLORE ALL PERFUMES','/products','combo',1,60);
INSERT INTO "banners" VALUES(2,'Tam Dao (SRK Edition)','Rich Mysore sandalwood, Italian cedar, and velvety oriental spices.','/products/tam-dao-srk','banner_20261005_105147_Hero_Banner_2_b56114_medium.webp',2,1,0,'2026-09-30 14:16:37.382816','BESTSELLER SPOTLIGHT','BUY NOW','','/combos','product',1,60);
INSERT INTO "banners" VALUES(3,'Complimentary Shipping','','/products','banner_20261006_131712_Complimentary_Shipping_L_de66a4_medium.webp',3,1,0,'2026-09-30 14:16:37.383345',NULL,NULL,NULL,NULL,NULL,NULL,55);
CREATE TABLE categories (
	id INTEGER NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	slug VARCHAR(100) NOT NULL, 
	description TEXT, 
	image_url VARCHAR(255), 
	display_order INTEGER NOT NULL, 
	active BOOLEAN NOT NULL, 
	is_deleted BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
INSERT INTO "categories" VALUES(1,'Fine Fragrances','fine-fragrances','Original Manufacturer oil made only Eau de Parfums inspired by the world''s most iconic scents.','cat_20261006_130931_Luxury_Perfume_Still_Lif_a4471f_medium.webp',1,1,0,'2026-09-30 14:16:37.352856','2026-10-06 07:39:32.152999');
INSERT INTO "categories" VALUES(2,'Luxury Car Perfumes','car-perfumes','Artisanal hanging wooden diffusers crafted with premium French fragrance oils for lasting automotive elegance.','cat_20261006_130953_Amber_Car_Diffuser_in_Su_280477_medium.webp',2,1,0,'2026-09-30 14:16:37.353807','2026-10-06 07:39:53.612360');
INSERT INTO "categories" VALUES(5,'For Him','for-him','','cat_20261006_131245_Warm_Amber_Fragrance_Sti_a69fee_medium.webp',4,1,0,'2026-10-05 11:35:54.720128','2026-10-06 07:42:45.943718');
INSERT INTO "categories" VALUES(6,'For Her','for-her','','cat_20261006_131438_Blush_Perfume_Vanity_Sti_4aeceb_medium.webp',4,1,0,'2026-10-06 07:44:38.930892','2026-10-06 07:44:38.930896');
CREATE TABLE combo_items (
	id INTEGER NOT NULL, 
	combo_id INTEGER NOT NULL, 
	product_variant_id INTEGER NOT NULL, 
	quantity INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(combo_id) REFERENCES combos (id) ON DELETE CASCADE, 
	FOREIGN KEY(product_variant_id) REFERENCES product_variants (id) ON DELETE RESTRICT
);
INSERT INTO "combo_items" VALUES(1,1,2,1);
INSERT INTO "combo_items" VALUES(2,1,55,1);
INSERT INTO "combo_items" VALUES(3,1,53,1);
INSERT INTO "combo_items" VALUES(4,1,45,1);
INSERT INTO "combo_items" VALUES(5,2,69,1);
INSERT INTO "combo_items" VALUES(6,2,71,1);
INSERT INTO "combo_items" VALUES(7,2,73,1);
INSERT INTO "combo_items" VALUES(8,3,2,1);
INSERT INTO "combo_items" VALUES(9,3,69,1);
CREATE TABLE combos (
	id INTEGER NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	slug VARCHAR(160) NOT NULL, 
	short_description VARCHAR(255), 
	full_description TEXT, 
	combo_price NUMERIC(10, 2) NOT NULL, 
	image_key VARCHAR(255), 
	display_order INTEGER NOT NULL, 
	active BOOLEAN NOT NULL, 
	is_deleted BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
INSERT INTO "combos" VALUES(1,'Prestige Quad Collection (Buy 4 @ ₹2249 Offer)','prestige-quad-collection-offer','Special offer bundle: 4 signature 50ml Eau de Parfums at ₹2249 flat.','Exclusive pre-launch special offer! Get 4 of our most coveted 50ml Eau de Parfums: Tam Dao (SRK), Creed Silver Mountain (Shahid Kapoor/Virat Kohli), Roja Mischief (Hardik Pandya), and Davidoff Cool Water (Akshay Kumar).',2249,'/static/images/perfume_sample.webp',1,1,0,'2026-10-01 06:43:13.809253','2026-10-01 06:43:13.809256');
INSERT INTO "combos" VALUES(2,'Luxury Car Diffuser Trio Collection','luxury-car-diffuser-trio','Artisanal 3-bottle car perfume collection (Gold, Black, & Frosted glass diffusers).','Elevate every drive with our 3-bottle luxury car perfume collection featuring Amber Noir, Citrus Velvet, and Royal Oud. Beautifully crafted with wooden diffusion caps.',849,'/static/images/car_sample.webp',2,1,0,'2026-10-01 06:43:13.817745','2026-10-01 06:43:13.817748');
INSERT INTO "combos" VALUES(3,'Executive Duo (Tam Dao 50ml + Amber Noir Car Diffuser)','executive-duo-tam-dao-car','Personal signature perfume paired with premium car diffuser.','Signature warmth wherever you go: Tam Dao (SRK) 50ml Eau de Parfum paired with Amber Noir Luxury Car Diffuser 10ml.',899,'/static/images/perfume_sample.webp',3,1,0,'2026-10-01 06:43:13.818421','2026-10-01 06:43:13.818423');
CREATE TABLE customers (
	id INTEGER NOT NULL, 
	phone VARCHAR(15) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	email VARCHAR(120), 
	address_line1 VARCHAR(255), 
	address_line2 VARCHAR(255), 
	city VARCHAR(100), 
	state VARCHAR(100), 
	pincode VARCHAR(10), 
	user_id INTEGER, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);
INSERT INTO "customers" VALUES(1,'7020651871','rajeev chouhan','crajeev351@gmail.com','c-303 Raagdari Apartments , Opposite Kaka Halwai , Aundh , 411007','Near westend mall','Pune','Maharastra','411007',1,'2026-10-01 06:54:27.886619','2026-10-05 11:19:36.005628');
INSERT INTO "customers" VALUES(2,'9893574573','Neha Sharma','neha.sharma@outlook.com','12B, Bandra West, Hill Road',NULL,'Mumbai','Maharashtra','400050',NULL,'2026-10-01 06:54:27.886625','2026-10-01 06:54:27.886626');
INSERT INTO "customers" VALUES(3,'9841993858','Tanvi Sharma','tanvi.s@gmail.com','Plot 18, Road No. 10, Jubilee Hills',NULL,'Hyderabad','Telangana','500033',NULL,'2026-10-01 06:54:27.886627','2026-10-01 06:54:27.886628');
INSERT INTO "customers" VALUES(4,'9815538051','Meera Sharma','meera.sharma@yahoo.com','C-44, Hauz Khas Enclave',NULL,'Delhi','Delhi','110017',NULL,'2026-10-01 06:54:27.886628','2026-10-01 06:54:27.886629');
INSERT INTO "customers" VALUES(5,'9820123456','Aarav Kapoor','aarav.kapoor@gmail.com','77, 100 Feet Road, Indiranagar',NULL,'Bengaluru','Karnataka','560038',NULL,'2026-10-01 06:54:27.886630','2026-10-01 06:54:27.886630');
INSERT INTO "customers" VALUES(6,'9847055123','Priya Nair','priya.nair@hotmail.com','Panampilly Nagar, Main Avenue',NULL,'Kochi','Kerala','682020',NULL,'2026-10-01 06:54:27.886631','2026-10-01 06:54:27.886632');
INSERT INTO "customers" VALUES(7,'9910456789','Aditya Verma','aditya.v@gmail.com','Tower 3, DLF Phase 5, Golf Course Road',NULL,'Gurugram','Haryana','122002',NULL,'2026-10-01 06:54:27.886632','2026-10-01 06:54:27.886633');
INSERT INTO "customers" VALUES(8,'9823098765','Rohan Deshmukh','rohan.d@gmail.com','Civil Lines, Near High Court',NULL,'Nagpur','Maharashtra','440010',NULL,'2026-10-01 06:54:27.886633','2026-10-01 06:54:27.886634');
INSERT INTO "customers" VALUES(9,'9830112233','Ananya Sen','ananya.sen@gmail.com','Ballygunge Circular Road, Flat 3A',NULL,'Kolkata','West Bengal','700019',NULL,'2026-10-01 06:54:27.886635','2026-10-01 06:54:27.886635');
INSERT INTO "customers" VALUES(10,'9829033445','Vikram Singhania','vikram.s@singhania.in','C-Scheme, Subhash Marg',NULL,'Jaipur','Rajasthan','302001',NULL,'2026-10-01 06:54:27.886636','2026-10-01 06:54:27.886636');
INSERT INTO "customers" VALUES(11,'9845012398','Kavita Rao','kavita.rao@gmail.com','Lavelle Road, Richmond Town',NULL,'Bengaluru','Karnataka','560001',NULL,'2026-10-01 06:54:27.886637','2026-10-01 06:54:27.886638');
INSERT INTO "customers" VALUES(12,'9892019283','Zaid Khan','zaid.khan@gmail.com','Lokhandwala Complex, Andheri West',NULL,'Mumbai','Maharashtra','400053',NULL,'2026-10-01 06:54:27.886638','2026-10-01 06:54:27.886639');
INSERT INTO "customers" VALUES(13,'9871234567','Siddharth Jain','siddharth.j@gmail.com','Bodakdev, SG Highway',NULL,'Ahmedabad','Gujarat','380015',NULL,'2026-10-01 06:54:27.886640','2026-10-01 06:54:27.886640');
INSERT INTO "customers" VALUES(14,'9811098765','Pooja Malhotra','pooja.m@gmail.com','Sector 9-C, Inner Ring Road',NULL,'Chandigarh','Punjab','160009',NULL,'2026-10-01 06:54:27.886641','2026-10-01 06:54:27.886641');
INSERT INTO "customers" VALUES(15,'9831987654','Ishaan Roy','ishaan.roy@gmail.com','Southern Avenue, Lake Terrace',NULL,'Kolkata','West Bengal','700029',NULL,'2026-10-01 06:54:27.886642','2026-10-01 06:54:27.886643');
INSERT INTO "customers" VALUES(16,'9849012345','Divya Reddy','divya.reddy@gmail.com','Madhapur, Hitec City Phase 2',NULL,'Hyderabad','Telangana','500081',NULL,'2026-10-01 06:54:27.886643','2026-10-01 06:54:27.886644');
CREATE TABLE order_counters (
	id INTEGER NOT NULL, 
	date_str VARCHAR(8) NOT NULL, 
	last_seq INTEGER NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
INSERT INTO "order_counters" VALUES(1,'20261001',5,'2026-10-01 06:54:28.014440');
INSERT INTO "order_counters" VALUES(2,'20260930',5,'2026-10-01 06:54:28.014443');
INSERT INTO "order_counters" VALUES(3,'20260929',4,'2026-10-01 06:54:28.014444');
INSERT INTO "order_counters" VALUES(4,'20260928',4,'2026-10-01 06:54:28.014445');
INSERT INTO "order_counters" VALUES(5,'20260927',3,'2026-10-01 06:54:28.014446');
INSERT INTO "order_counters" VALUES(6,'20260926',3,'2026-10-01 06:54:28.014447');
INSERT INTO "order_counters" VALUES(7,'20260925',3,'2026-10-01 06:54:28.014447');
INSERT INTO "order_counters" VALUES(8,'20260924',3,'2026-10-01 06:54:28.014448');
INSERT INTO "order_counters" VALUES(9,'20260922',2,'2026-10-01 06:54:28.014448');
INSERT INTO "order_counters" VALUES(10,'20260920',2,'2026-10-01 06:54:28.014449');
INSERT INTO "order_counters" VALUES(11,'20260918',1,'2026-10-01 06:54:28.014450');
INSERT INTO "order_counters" VALUES(12,'20261004',1,'2026-10-04 10:54:26.797363');
INSERT INTO "order_counters" VALUES(13,'20261005',2,'2026-10-05 17:02:34.254712');
CREATE TABLE order_items (
	id INTEGER NOT NULL, 
	order_id INTEGER NOT NULL, 
	product_variant_id INTEGER, 
	product_name_snapshot VARCHAR(150) NOT NULL, 
	variant_label_snapshot VARCHAR(50) NOT NULL, 
	sku_snapshot VARCHAR(64) NOT NULL, 
	unit_price_snapshot NUMERIC(10, 2) NOT NULL, 
	quantity INTEGER NOT NULL, 
	total_price NUMERIC(10, 2) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE CASCADE, 
	FOREIGN KEY(product_variant_id) REFERENCES product_variants (id) ON DELETE SET NULL
);
INSERT INTO "order_items" VALUES(1,1,2,'Tam Dao (SRK)','50ml EDP','TAM-DAO--50ML',649,1,649,'2026-10-01 08:34:00.000000');
INSERT INTO "order_items" VALUES(2,1,55,'Creed Silver Mountain (Shahid Kapoor/ Virat Kohli)','50ml EDP','CREED-SI-50ML',649,1,649,'2026-10-01 08:34:00.000000');
INSERT INTO "order_items" VALUES(3,2,7,'Azzaro Most Wanted','30ml EDP','AZZARO-M-30ML',380,1,380,'2026-10-01 07:54:00.000000');
INSERT INTO "order_items" VALUES(4,2,10,'YSL Libre','30ml EDP','YSL-LIBR-30ML',380,1,380,'2026-10-01 07:54:00.000000');
INSERT INTO "order_items" VALUES(5,2,4,'Burberry Weekend','30ml EDP','BURBERRY-30ML',380,1,380,'2026-10-01 07:54:00.000000');
INSERT INTO "order_items" VALUES(6,3,32,'CR7 (Cristiano Ronaldo)','100ml EDP','CR7-CRIS-100ML',1149,1,1149,'2026-10-01 05:14:00.000000');
INSERT INTO "order_items" VALUES(7,3,69,'Amber Noir Luxury Car Diffuser','10ml Hanging Diffuser','CAR-AMBER--10ML',349,1,349,'2026-10-01 05:14:00.000000');
INSERT INTO "order_items" VALUES(8,4,53,'Roja Mischief (Hardik Pandya)','50ml EDP','ROJA-MIS-50ML',649,1,649,'2026-10-01 10:13:00.000000');
INSERT INTO "order_items" VALUES(9,4,45,'Davidoff Cool Water (Akshay Kumar)','50ml EDP','DAVIDOFF-50ML',649,1,649,'2026-10-01 10:13:00.000000');
INSERT INTO "order_items" VALUES(10,5,44,'Tom Ford Vanilla','100ml EDP','TOM-FORD-100ML',1149,1,1149,'2026-10-01 04:15:00.000000');
INSERT INTO "order_items" VALUES(11,6,72,'Citrus Velvet Luxury Car Diffuser','Twin Pack (2 x 10ml)','CAR-CITRUS-20ML',599,1,599,'2026-09-30 08:51:00.000000');
INSERT INTO "order_items" VALUES(12,6,16,'Dior Homme','30ml EDP','DIOR-HOM-30ML',380,1,380,'2026-09-30 08:51:00.000000');
INSERT INTO "order_items" VALUES(13,7,37,'Khamrah Qahwa','50ml EDP','KHAMRAH--50ML',649,1,649,'2026-09-30 04:30:00.000000');
INSERT INTO "order_items" VALUES(14,7,49,'Carolina Herrera - Good Girl','50ml EDP','CAROLINA-50ML',649,1,649,'2026-09-30 04:30:00.000000');
INSERT INTO "order_items" VALUES(15,8,73,'Royal Oud & Woods Luxury Car Diffuser','10ml Hanging Diffuser','CAR-ROYAL--10ML',349,2,698,'2026-09-30 07:13:00.000000');
INSERT INTO "order_items" VALUES(16,8,75,'Aqua Marine Breeze Luxury Car Diffuser','10ml Hanging Diffuser','CAR-AQUA-M-10ML',349,1,349,'2026-09-30 07:13:00.000000');
INSERT INTO "order_items" VALUES(17,9,35,'Imagination','50ml EDP','IMAGINAT-50ML',649,1,649,'2026-09-30 09:08:00.000000');
INSERT INTO "order_items" VALUES(18,9,39,'Astral (FIFA)','50ml EDP','ASTRAL-F-50ML',649,1,649,'2026-09-30 09:08:00.000000');
INSERT INTO "order_items" VALUES(19,10,19,'Imperial Valley','30ml EDP','IMPERIAL-30ML',380,1,380,'2026-09-30 03:39:00.000000');
INSERT INTO "order_items" VALUES(20,11,61,'Versace Eros','50ml EDP','VERSACE--50ML',649,1,649,'2026-09-29 08:05:00.000000');
INSERT INTO "order_items" VALUES(21,11,63,'Men in Black','50ml EDP','MEN-IN-B-50ML',649,1,649,'2026-09-29 08:05:00.000000');
INSERT INTO "order_items" VALUES(22,12,65,'YSL Mon Paris','50ml EDP','YSL-MON--50ML',649,1,649,'2026-09-29 07:05:00.000000');
INSERT INTO "order_items" VALUES(23,12,67,'Balmain Paris','50ml EDP','BALMAIN--50ML',649,1,649,'2026-09-29 07:05:00.000000');
INSERT INTO "order_items" VALUES(24,13,52,'Dubai Gold','100ml EDP','DUBAI-GO-100ML',1149,1,1149,'2026-09-29 03:23:00.000000');
INSERT INTO "order_items" VALUES(25,13,48,'Club de Nuit Armaf','100ml EDP','CLUB-DE--100ML',1149,1,1149,'2026-09-29 03:23:00.000000');
INSERT INTO "order_items" VALUES(26,14,1,'Tam Dao (SRK)','30ml EDP','TAM-DAO--30ML',380,1,380,'2026-09-29 06:53:00.000000');
INSERT INTO "order_items" VALUES(27,14,13,'Armani Tobacco','30ml EDP','ARMANI-T-30ML',380,1,380,'2026-09-29 06:53:00.000000');
INSERT INTO "order_items" VALUES(28,14,22,'Gucci Guilty','30ml EDP','GUCCI-GU-30ML',380,1,380,'2026-09-29 06:53:00.000000');
INSERT INTO "order_items" VALUES(29,15,42,'Aggressive','100ml EDP','AGGRESSI-100ML',1149,1,1149,'2026-09-28 03:38:00.000000');
INSERT INTO "order_items" VALUES(30,15,70,'Amber Noir Luxury Car Diffuser','Twin Pack (2 x 10ml)','CAR-AMBER--20ML',599,1,599,'2026-09-28 03:38:00.000000');
INSERT INTO "order_items" VALUES(31,16,2,'Tam Dao (SRK)','50ml EDP','TAM-DAO--50ML',649,1,649,'2026-09-28 06:40:00.000000');
INSERT INTO "order_items" VALUES(32,16,55,'Creed Silver Mountain (Shahid Kapoor/ Virat Kohli)','50ml EDP','CREED-SI-50ML',649,1,649,'2026-09-28 06:40:00.000000');
INSERT INTO "order_items" VALUES(33,17,7,'Azzaro Most Wanted','30ml EDP','AZZARO-M-30ML',380,1,380,'2026-09-28 09:43:00.000000');
INSERT INTO "order_items" VALUES(34,17,10,'YSL Libre','30ml EDP','YSL-LIBR-30ML',380,1,380,'2026-09-28 09:43:00.000000');
INSERT INTO "order_items" VALUES(35,17,4,'Burberry Weekend','30ml EDP','BURBERRY-30ML',380,1,380,'2026-09-28 09:43:00.000000');
INSERT INTO "order_items" VALUES(36,18,32,'CR7 (Cristiano Ronaldo)','100ml EDP','CR7-CRIS-100ML',1149,1,1149,'2026-09-28 09:43:00.000000');
INSERT INTO "order_items" VALUES(37,18,69,'Amber Noir Luxury Car Diffuser','10ml Hanging Diffuser','CAR-AMBER--10ML',349,1,349,'2026-09-28 09:43:00.000000');
INSERT INTO "order_items" VALUES(38,19,53,'Roja Mischief (Hardik Pandya)','50ml EDP','ROJA-MIS-50ML',649,1,649,'2026-09-27 03:25:00.000000');
INSERT INTO "order_items" VALUES(39,19,45,'Davidoff Cool Water (Akshay Kumar)','50ml EDP','DAVIDOFF-50ML',649,1,649,'2026-09-27 03:25:00.000000');
INSERT INTO "order_items" VALUES(40,20,44,'Tom Ford Vanilla','100ml EDP','TOM-FORD-100ML',1149,1,1149,'2026-09-27 03:13:00.000000');
INSERT INTO "order_items" VALUES(41,21,72,'Citrus Velvet Luxury Car Diffuser','Twin Pack (2 x 10ml)','CAR-CITRUS-20ML',599,1,599,'2026-09-27 09:52:00.000000');
INSERT INTO "order_items" VALUES(42,21,16,'Dior Homme','30ml EDP','DIOR-HOM-30ML',380,1,380,'2026-09-27 09:52:00.000000');
INSERT INTO "order_items" VALUES(43,22,37,'Khamrah Qahwa','50ml EDP','KHAMRAH--50ML',649,1,649,'2026-09-26 10:20:00.000000');
INSERT INTO "order_items" VALUES(44,22,49,'Carolina Herrera - Good Girl','50ml EDP','CAROLINA-50ML',649,1,649,'2026-09-26 10:20:00.000000');
INSERT INTO "order_items" VALUES(45,23,73,'Royal Oud & Woods Luxury Car Diffuser','10ml Hanging Diffuser','CAR-ROYAL--10ML',349,2,698,'2026-09-26 03:13:00.000000');
INSERT INTO "order_items" VALUES(46,23,75,'Aqua Marine Breeze Luxury Car Diffuser','10ml Hanging Diffuser','CAR-AQUA-M-10ML',349,1,349,'2026-09-26 03:13:00.000000');
INSERT INTO "order_items" VALUES(47,24,35,'Imagination','50ml EDP','IMAGINAT-50ML',649,1,649,'2026-09-26 07:15:00.000000');
INSERT INTO "order_items" VALUES(48,24,39,'Astral (FIFA)','50ml EDP','ASTRAL-F-50ML',649,1,649,'2026-09-26 07:15:00.000000');
INSERT INTO "order_items" VALUES(49,25,19,'Imperial Valley','30ml EDP','IMPERIAL-30ML',380,1,380,'2026-09-25 05:09:00.000000');
INSERT INTO "order_items" VALUES(50,26,61,'Versace Eros','50ml EDP','VERSACE--50ML',649,1,649,'2026-09-25 07:05:00.000000');
INSERT INTO "order_items" VALUES(51,26,63,'Men in Black','50ml EDP','MEN-IN-B-50ML',649,1,649,'2026-09-25 07:05:00.000000');
INSERT INTO "order_items" VALUES(52,27,65,'YSL Mon Paris','50ml EDP','YSL-MON--50ML',649,1,649,'2026-09-25 10:29:00.000000');
INSERT INTO "order_items" VALUES(53,27,67,'Balmain Paris','50ml EDP','BALMAIN--50ML',649,1,649,'2026-09-25 10:29:00.000000');
INSERT INTO "order_items" VALUES(54,28,52,'Dubai Gold','100ml EDP','DUBAI-GO-100ML',1149,1,1149,'2026-09-24 10:37:00.000000');
INSERT INTO "order_items" VALUES(55,28,48,'Club de Nuit Armaf','100ml EDP','CLUB-DE--100ML',1149,1,1149,'2026-09-24 10:37:00.000000');
INSERT INTO "order_items" VALUES(56,29,1,'Tam Dao (SRK)','30ml EDP','TAM-DAO--30ML',380,1,380,'2026-09-24 03:07:00.000000');
INSERT INTO "order_items" VALUES(57,29,13,'Armani Tobacco','30ml EDP','ARMANI-T-30ML',380,1,380,'2026-09-24 03:07:00.000000');
INSERT INTO "order_items" VALUES(58,29,22,'Gucci Guilty','30ml EDP','GUCCI-GU-30ML',380,1,380,'2026-09-24 03:07:00.000000');
INSERT INTO "order_items" VALUES(59,30,42,'Aggressive','100ml EDP','AGGRESSI-100ML',1149,1,1149,'2026-09-24 09:42:00.000000');
INSERT INTO "order_items" VALUES(60,30,70,'Amber Noir Luxury Car Diffuser','Twin Pack (2 x 10ml)','CAR-AMBER--20ML',599,1,599,'2026-09-24 09:42:00.000000');
INSERT INTO "order_items" VALUES(61,31,2,'Tam Dao (SRK)','50ml EDP','TAM-DAO--50ML',649,1,649,'2026-09-22 06:26:00.000000');
INSERT INTO "order_items" VALUES(62,31,55,'Creed Silver Mountain (Shahid Kapoor/ Virat Kohli)','50ml EDP','CREED-SI-50ML',649,1,649,'2026-09-22 06:26:00.000000');
INSERT INTO "order_items" VALUES(63,32,7,'Azzaro Most Wanted','30ml EDP','AZZARO-M-30ML',380,1,380,'2026-09-22 08:47:00.000000');
INSERT INTO "order_items" VALUES(64,32,10,'YSL Libre','30ml EDP','YSL-LIBR-30ML',380,1,380,'2026-09-22 08:47:00.000000');
INSERT INTO "order_items" VALUES(65,32,4,'Burberry Weekend','30ml EDP','BURBERRY-30ML',380,1,380,'2026-09-22 08:47:00.000000');
INSERT INTO "order_items" VALUES(66,33,32,'CR7 (Cristiano Ronaldo)','100ml EDP','CR7-CRIS-100ML',1149,1,1149,'2026-09-20 09:11:00.000000');
INSERT INTO "order_items" VALUES(67,33,69,'Amber Noir Luxury Car Diffuser','10ml Hanging Diffuser','CAR-AMBER--10ML',349,1,349,'2026-09-20 09:11:00.000000');
INSERT INTO "order_items" VALUES(68,34,53,'Roja Mischief (Hardik Pandya)','50ml EDP','ROJA-MIS-50ML',649,1,649,'2026-09-20 09:24:00.000000');
INSERT INTO "order_items" VALUES(69,34,45,'Davidoff Cool Water (Akshay Kumar)','50ml EDP','DAVIDOFF-50ML',649,1,649,'2026-09-20 09:24:00.000000');
INSERT INTO "order_items" VALUES(70,35,44,'Tom Ford Vanilla','100ml EDP','TOM-FORD-100ML',1149,1,1149,'2026-09-18 07:25:00.000000');
INSERT INTO "order_items" VALUES(71,36,1,'Tam Dao (SRK)','30ml EDP','TAM-DAO--30ML',380,1,380,'2026-10-04 10:54:26.802460');
INSERT INTO "order_items" VALUES(72,37,16,'Dior Homme','30ml EDP','DIOR-HOM-30ML',380,1,380,'2026-10-05 11:19:36.020132');
INSERT INTO "order_items" VALUES(73,38,65,'YSL Mon Paris','50ml EDP','YSL-MON--50ML',649,1,649,'2026-10-05 17:02:34.257536');
CREATE TABLE order_status_history (
	id INTEGER NOT NULL, 
	order_id INTEGER NOT NULL, 
	status VARCHAR(32) NOT NULL, 
	title VARCHAR(100) NOT NULL, 
	notes VARCHAR(255), 
	created_by VARCHAR(64) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE CASCADE
);
INSERT INTO "order_status_history" VALUES(1,1,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-10-01 08:34:00.000000');
INSERT INTO "order_status_history" VALUES(2,1,'PAID','Payment Verified','Payment received and verified.','Store Admin','2026-10-01 08:49:00.000000');
INSERT INTO "order_status_history" VALUES(3,1,'CONFIRMED','Order Confirmed','Order confirmed and assigned for packaging.','Store Admin','2026-10-01 08:54:00.000000');
INSERT INTO "order_status_history" VALUES(4,1,'PACKED','Order Packed','Items inspected and safely packaged in protective bubble wrap.','Store Admin','2026-10-01 09:39:00.000000');
INSERT INTO "order_status_history" VALUES(5,1,'SHIPPED','Order Shipped','Handed over to BlueDart Express. Tracking AWB: BD0001IN','Store Admin','2026-10-01 12:39:00.000000');
INSERT INTO "order_status_history" VALUES(6,1,'DELIVERED','Delivered','Shipment successfully delivered to recipient.','Store Admin','2026-10-03 12:39:00.000000');
INSERT INTO "order_status_history" VALUES(7,2,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-10-01 07:54:00.000000');
INSERT INTO "order_status_history" VALUES(8,3,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-10-01 05:14:00.000000');
INSERT INTO "order_status_history" VALUES(9,4,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-10-01 10:13:00.000000');
INSERT INTO "order_status_history" VALUES(10,4,'PAID','Payment Verified','Payment received and verified.','Store Admin','2026-10-01 10:28:00.000000');
INSERT INTO "order_status_history" VALUES(11,4,'CONFIRMED','Order Confirmed','Order confirmed and assigned for packaging.','Store Admin','2026-10-01 10:33:00.000000');
INSERT INTO "order_status_history" VALUES(12,5,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-10-01 04:15:00.000000');
INSERT INTO "order_status_history" VALUES(13,5,'PAID','Payment Verified','Payment received and verified.','Store Admin','2026-10-01 04:30:00.000000');
INSERT INTO "order_status_history" VALUES(14,5,'CONFIRMED','Order Confirmed','Order confirmed and assigned for packaging.','Store Admin','2026-10-01 04:35:00.000000');
INSERT INTO "order_status_history" VALUES(15,6,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-09-30 08:51:00.000000');
INSERT INTO "order_status_history" VALUES(16,7,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-09-30 04:30:00.000000');
INSERT INTO "order_status_history" VALUES(17,7,'PAID','Payment Verified','Payment received and verified.','Store Admin','2026-09-30 04:45:00.000000');
INSERT INTO "order_status_history" VALUES(18,7,'CONFIRMED','Order Confirmed','Order confirmed and assigned for packaging.','Store Admin','2026-09-30 04:50:00.000000');
INSERT INTO "order_status_history" VALUES(19,7,'PACKED','Order Packed','Items inspected and safely packaged in protective bubble wrap.','Store Admin','2026-09-30 05:35:00.000000');
INSERT INTO "order_status_history" VALUES(20,8,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-09-30 07:13:00.000000');
INSERT INTO "order_status_history" VALUES(21,8,'PAID','Payment Verified','Payment received and verified.','Store Admin','2026-09-30 07:28:00.000000');
INSERT INTO "order_status_history" VALUES(22,8,'CONFIRMED','Order Confirmed','Order confirmed and assigned for packaging.','Store Admin','2026-09-30 07:33:00.000000');
INSERT INTO "order_status_history" VALUES(23,8,'PACKED','Order Packed','Items inspected and safely packaged in protective bubble wrap.','Store Admin','2026-09-30 08:18:00.000000');
INSERT INTO "order_status_history" VALUES(24,9,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-09-30 09:08:00.000000');
INSERT INTO "order_status_history" VALUES(25,9,'PAID','Payment Verified','Payment received and verified.','Store Admin','2026-09-30 09:23:00.000000');
INSERT INTO "order_status_history" VALUES(26,9,'CONFIRMED','Order Confirmed','Order confirmed and assigned for packaging.','Store Admin','2026-09-30 09:28:00.000000');
INSERT INTO "order_status_history" VALUES(27,10,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-09-30 03:39:00.000000');
INSERT INTO "order_status_history" VALUES(28,10,'PAID','Payment Verified','Payment received and verified.','Store Admin','2026-09-30 03:54:00.000000');
INSERT INTO "order_status_history" VALUES(29,10,'CONFIRMED','Order Confirmed','Order confirmed and assigned for packaging.','Store Admin','2026-09-30 03:59:00.000000');
INSERT INTO "order_status_history" VALUES(30,11,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-09-29 08:05:00.000000');
INSERT INTO "order_status_history" VALUES(31,11,'PAID','Payment Verified','Payment received and verified.','Store Admin','2026-09-29 08:20:00.000000');
INSERT INTO "order_status_history" VALUES(32,11,'CONFIRMED','Order Confirmed','Order confirmed and assigned for packaging.','Store Admin','2026-09-29 08:25:00.000000');
INSERT INTO "order_status_history" VALUES(33,11,'PACKED','Order Packed','Items inspected and safely packaged in protective bubble wrap.','Store Admin','2026-09-29 09:10:00.000000');
INSERT INTO "order_status_history" VALUES(34,12,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-09-29 07:05:00.000000');
INSERT INTO "order_status_history" VALUES(35,12,'PAID','Payment Verified','Payment received and verified.','Store Admin','2026-09-29 07:20:00.000000');
INSERT INTO "order_status_history" VALUES(36,12,'CONFIRMED','Order Confirmed','Order confirmed and assigned for packaging.','Store Admin','2026-09-29 07:25:00.000000');
INSERT INTO "order_status_history" VALUES(37,12,'PACKED','Order Packed','Items inspected and safely packaged in protective bubble wrap.','Store Admin','2026-09-29 08:10:00.000000');
INSERT INTO "order_status_history" VALUES(38,12,'SHIPPED','Order Shipped','Handed over to BlueDart Express. Tracking AWB: BD0012IN','Store Admin','2026-09-29 11:10:00.000000');
INSERT INTO "order_status_history" VALUES(39,13,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-09-29 03:23:00.000000');
INSERT INTO "order_status_history" VALUES(40,13,'PAID','Payment Verified','Payment received and verified.','Store Admin','2026-09-29 03:38:00.000000');
INSERT INTO "order_status_history" VALUES(41,13,'CONFIRMED','Order Confirmed','Order confirmed and assigned for packaging.','Store Admin','2026-09-29 03:43:00.000000');
INSERT INTO "order_status_history" VALUES(42,13,'PACKED','Order Packed','Items inspected and safely packaged in protective bubble wrap.','Store Admin','2026-09-29 04:28:00.000000');
INSERT INTO "order_status_history" VALUES(43,13,'SHIPPED','Order Shipped','Handed over to BlueDart Express. Tracking AWB: BD0013IN','Store Admin','2026-09-29 07:28:00.000000');
INSERT INTO "order_status_history" VALUES(44,14,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-09-29 06:53:00.000000');
INSERT INTO "order_status_history" VALUES(45,14,'PAID','Payment Verified','Payment received and verified.','Store Admin','2026-09-29 07:08:00.000000');
INSERT INTO "order_status_history" VALUES(46,14,'CONFIRMED','Order Confirmed','Order confirmed and assigned for packaging.','Store Admin','2026-09-29 07:13:00.000000');
INSERT INTO "order_status_history" VALUES(47,15,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-09-28 03:38:00.000000');
INSERT INTO "order_status_history" VALUES(48,15,'PAID','Payment Verified','Payment received and verified.','Store Admin','2026-09-28 03:53:00.000000');
INSERT INTO "order_status_history" VALUES(49,15,'CONFIRMED','Order Confirmed','Order confirmed and assigned for packaging.','Store Admin','2026-09-28 03:58:00.000000');
INSERT INTO "order_status_history" VALUES(50,15,'PACKED','Order Packed','Items inspected and safely packaged in protective bubble wrap.','Store Admin','2026-09-28 04:43:00.000000');
INSERT INTO "order_status_history" VALUES(51,15,'SHIPPED','Order Shipped','Handed over to BlueDart Express. Tracking AWB: BD0015IN','Store Admin','2026-09-28 07:43:00.000000');
INSERT INTO "order_status_history" VALUES(52,16,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-09-28 06:40:00.000000');
INSERT INTO "order_status_history" VALUES(53,16,'PAID','Payment Verified','Payment received and verified.','Store Admin','2026-09-28 06:55:00.000000');
INSERT INTO "order_status_history" VALUES(54,16,'CONFIRMED','Order Confirmed','Order confirmed and assigned for packaging.','Store Admin','2026-09-28 07:00:00.000000');
INSERT INTO "order_status_history" VALUES(55,16,'PACKED','Order Packed','Items inspected and safely packaged in protective bubble wrap.','Store Admin','2026-09-28 07:45:00.000000');
INSERT INTO "order_status_history" VALUES(56,16,'SHIPPED','Order Shipped','Handed over to BlueDart Express. Tracking AWB: BD0016IN','Store Admin','2026-09-28 10:45:00.000000');
INSERT INTO "order_status_history" VALUES(57,16,'DELIVERED','Delivered','Shipment successfully delivered to recipient.','Store Admin','2026-09-30 10:45:00.000000');
INSERT INTO "order_status_history" VALUES(58,17,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-09-28 09:43:00.000000');
INSERT INTO "order_status_history" VALUES(59,17,'PAID','Payment Verified','Payment received and verified.','Store Admin','2026-09-28 09:58:00.000000');
INSERT INTO "order_status_history" VALUES(60,17,'CONFIRMED','Order Confirmed','Order confirmed and assigned for packaging.','Store Admin','2026-09-28 10:03:00.000000');
INSERT INTO "order_status_history" VALUES(61,17,'PACKED','Order Packed','Items inspected and safely packaged in protective bubble wrap.','Store Admin','2026-09-28 10:48:00.000000');
INSERT INTO "order_status_history" VALUES(62,17,'SHIPPED','Order Shipped','Handed over to BlueDart Express. Tracking AWB: BD0017IN','Store Admin','2026-09-28 13:48:00.000000');
INSERT INTO "order_status_history" VALUES(63,17,'DELIVERED','Delivered','Shipment successfully delivered to recipient.','Store Admin','2026-09-30 13:48:00.000000');
INSERT INTO "order_status_history" VALUES(64,18,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-09-28 09:43:00.000000');
INSERT INTO "order_status_history" VALUES(65,19,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-09-27 03:25:00.000000');
INSERT INTO "order_status_history" VALUES(66,19,'PAID','Payment Verified','Payment received and verified.','Store Admin','2026-09-27 03:40:00.000000');
INSERT INTO "order_status_history" VALUES(67,19,'CONFIRMED','Order Confirmed','Order confirmed and assigned for packaging.','Store Admin','2026-09-27 03:45:00.000000');
INSERT INTO "order_status_history" VALUES(68,19,'PACKED','Order Packed','Items inspected and safely packaged in protective bubble wrap.','Store Admin','2026-09-27 04:30:00.000000');
INSERT INTO "order_status_history" VALUES(69,19,'SHIPPED','Order Shipped','Handed over to BlueDart Express. Tracking AWB: BD0019IN','Store Admin','2026-09-27 07:30:00.000000');
INSERT INTO "order_status_history" VALUES(70,19,'DELIVERED','Delivered','Shipment successfully delivered to recipient.','Store Admin','2026-09-29 07:30:00.000000');
INSERT INTO "order_status_history" VALUES(71,20,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-09-27 03:13:00.000000');
INSERT INTO "order_status_history" VALUES(72,20,'PAID','Payment Verified','Payment received and verified.','Store Admin','2026-09-27 03:28:00.000000');
INSERT INTO "order_status_history" VALUES(73,20,'CONFIRMED','Order Confirmed','Order confirmed and assigned for packaging.','Store Admin','2026-09-27 03:33:00.000000');
INSERT INTO "order_status_history" VALUES(74,20,'PACKED','Order Packed','Items inspected and safely packaged in protective bubble wrap.','Store Admin','2026-09-27 04:18:00.000000');
INSERT INTO "order_status_history" VALUES(75,20,'SHIPPED','Order Shipped','Handed over to BlueDart Express. Tracking AWB: BD0020IN','Store Admin','2026-09-27 07:18:00.000000');
INSERT INTO "order_status_history" VALUES(76,21,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-09-27 09:52:00.000000');
INSERT INTO "order_status_history" VALUES(77,21,'PAID','Payment Verified','Payment received and verified.','Store Admin','2026-09-27 10:07:00.000000');
INSERT INTO "order_status_history" VALUES(78,21,'CONFIRMED','Order Confirmed','Order confirmed and assigned for packaging.','Store Admin','2026-09-27 10:12:00.000000');
INSERT INTO "order_status_history" VALUES(79,21,'PACKED','Order Packed','Items inspected and safely packaged in protective bubble wrap.','Store Admin','2026-09-27 10:57:00.000000');
INSERT INTO "order_status_history" VALUES(80,22,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-09-26 10:20:00.000000');
INSERT INTO "order_status_history" VALUES(81,22,'PAID','Payment Verified','Payment received and verified.','Store Admin','2026-09-26 10:35:00.000000');
INSERT INTO "order_status_history" VALUES(82,22,'CONFIRMED','Order Confirmed','Order confirmed and assigned for packaging.','Store Admin','2026-09-26 10:40:00.000000');
INSERT INTO "order_status_history" VALUES(83,22,'PACKED','Order Packed','Items inspected and safely packaged in protective bubble wrap.','Store Admin','2026-09-26 11:25:00.000000');
INSERT INTO "order_status_history" VALUES(84,22,'SHIPPED','Order Shipped','Handed over to BlueDart Express. Tracking AWB: BD0022IN','Store Admin','2026-09-26 14:25:00.000000');
INSERT INTO "order_status_history" VALUES(85,22,'DELIVERED','Delivered','Shipment successfully delivered to recipient.','Store Admin','2026-09-28 14:25:00.000000');
INSERT INTO "order_status_history" VALUES(86,23,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-09-26 03:13:00.000000');
INSERT INTO "order_status_history" VALUES(87,23,'PAID','Payment Verified','Payment received and verified.','Store Admin','2026-09-26 03:28:00.000000');
INSERT INTO "order_status_history" VALUES(88,23,'CONFIRMED','Order Confirmed','Order confirmed and assigned for packaging.','Store Admin','2026-09-26 03:33:00.000000');
INSERT INTO "order_status_history" VALUES(89,23,'PACKED','Order Packed','Items inspected and safely packaged in protective bubble wrap.','Store Admin','2026-09-26 04:18:00.000000');
INSERT INTO "order_status_history" VALUES(90,23,'SHIPPED','Order Shipped','Handed over to BlueDart Express. Tracking AWB: BD0023IN','Store Admin','2026-09-26 07:18:00.000000');
INSERT INTO "order_status_history" VALUES(91,23,'DELIVERED','Delivered','Shipment successfully delivered to recipient.','Store Admin','2026-09-28 07:18:00.000000');
INSERT INTO "order_status_history" VALUES(92,24,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-09-26 07:15:00.000000');
INSERT INTO "order_status_history" VALUES(93,24,'CANCELLED','Order Cancelled','Order cancelled and reserved stock restored.','Store Admin','2026-09-26 08:15:00.000000');
INSERT INTO "order_status_history" VALUES(94,25,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-09-25 05:09:00.000000');
INSERT INTO "order_status_history" VALUES(95,25,'PAID','Payment Verified','Payment received and verified.','Store Admin','2026-09-25 05:24:00.000000');
INSERT INTO "order_status_history" VALUES(96,25,'CONFIRMED','Order Confirmed','Order confirmed and assigned for packaging.','Store Admin','2026-09-25 05:29:00.000000');
INSERT INTO "order_status_history" VALUES(97,25,'PACKED','Order Packed','Items inspected and safely packaged in protective bubble wrap.','Store Admin','2026-09-25 06:14:00.000000');
INSERT INTO "order_status_history" VALUES(98,25,'SHIPPED','Order Shipped','Handed over to BlueDart Express. Tracking AWB: BD0025IN','Store Admin','2026-09-25 09:14:00.000000');
INSERT INTO "order_status_history" VALUES(99,25,'DELIVERED','Delivered','Shipment successfully delivered to recipient.','Store Admin','2026-09-27 09:14:00.000000');
INSERT INTO "order_status_history" VALUES(100,26,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-09-25 07:05:00.000000');
INSERT INTO "order_status_history" VALUES(101,26,'PAID','Payment Verified','Payment received and verified.','Store Admin','2026-09-25 07:20:00.000000');
INSERT INTO "order_status_history" VALUES(102,26,'CONFIRMED','Order Confirmed','Order confirmed and assigned for packaging.','Store Admin','2026-09-25 07:25:00.000000');
INSERT INTO "order_status_history" VALUES(103,26,'PACKED','Order Packed','Items inspected and safely packaged in protective bubble wrap.','Store Admin','2026-09-25 08:10:00.000000');
INSERT INTO "order_status_history" VALUES(104,26,'SHIPPED','Order Shipped','Handed over to BlueDart Express. Tracking AWB: BD0026IN','Store Admin','2026-09-25 11:10:00.000000');
INSERT INTO "order_status_history" VALUES(105,26,'DELIVERED','Delivered','Shipment successfully delivered to recipient.','Store Admin','2026-09-27 11:10:00.000000');
INSERT INTO "order_status_history" VALUES(106,27,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-09-25 10:29:00.000000');
INSERT INTO "order_status_history" VALUES(107,27,'CANCELLED','Order Cancelled','Order cancelled and reserved stock restored.','Store Admin','2026-09-25 11:29:00.000000');
INSERT INTO "order_status_history" VALUES(108,28,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-09-24 10:37:00.000000');
INSERT INTO "order_status_history" VALUES(109,28,'PAID','Payment Verified','Payment received and verified.','Store Admin','2026-09-24 10:52:00.000000');
INSERT INTO "order_status_history" VALUES(110,28,'CONFIRMED','Order Confirmed','Order confirmed and assigned for packaging.','Store Admin','2026-09-24 10:57:00.000000');
INSERT INTO "order_status_history" VALUES(111,28,'PACKED','Order Packed','Items inspected and safely packaged in protective bubble wrap.','Store Admin','2026-09-24 11:42:00.000000');
INSERT INTO "order_status_history" VALUES(112,28,'SHIPPED','Order Shipped','Handed over to BlueDart Express. Tracking AWB: BD0028IN','Store Admin','2026-09-24 14:42:00.000000');
INSERT INTO "order_status_history" VALUES(113,28,'DELIVERED','Delivered','Shipment successfully delivered to recipient.','Store Admin','2026-09-26 14:42:00.000000');
INSERT INTO "order_status_history" VALUES(114,29,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-09-24 03:07:00.000000');
INSERT INTO "order_status_history" VALUES(115,29,'PAID','Payment Verified','Payment received and verified.','Store Admin','2026-09-24 03:22:00.000000');
INSERT INTO "order_status_history" VALUES(116,29,'CONFIRMED','Order Confirmed','Order confirmed and assigned for packaging.','Store Admin','2026-09-24 03:27:00.000000');
INSERT INTO "order_status_history" VALUES(117,29,'PACKED','Order Packed','Items inspected and safely packaged in protective bubble wrap.','Store Admin','2026-09-24 04:12:00.000000');
INSERT INTO "order_status_history" VALUES(118,29,'SHIPPED','Order Shipped','Handed over to BlueDart Express. Tracking AWB: BD0029IN','Store Admin','2026-09-24 07:12:00.000000');
INSERT INTO "order_status_history" VALUES(119,29,'DELIVERED','Delivered','Shipment successfully delivered to recipient.','Store Admin','2026-09-26 07:12:00.000000');
INSERT INTO "order_status_history" VALUES(120,30,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-09-24 09:42:00.000000');
INSERT INTO "order_status_history" VALUES(121,31,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-09-22 06:26:00.000000');
INSERT INTO "order_status_history" VALUES(122,31,'PAID','Payment Verified','Payment received and verified.','Store Admin','2026-09-22 06:41:00.000000');
INSERT INTO "order_status_history" VALUES(123,31,'CONFIRMED','Order Confirmed','Order confirmed and assigned for packaging.','Store Admin','2026-09-22 06:46:00.000000');
INSERT INTO "order_status_history" VALUES(124,31,'PACKED','Order Packed','Items inspected and safely packaged in protective bubble wrap.','Store Admin','2026-09-22 07:31:00.000000');
INSERT INTO "order_status_history" VALUES(125,31,'SHIPPED','Order Shipped','Handed over to BlueDart Express. Tracking AWB: BD0031IN','Store Admin','2026-09-22 10:31:00.000000');
INSERT INTO "order_status_history" VALUES(126,31,'DELIVERED','Delivered','Shipment successfully delivered to recipient.','Store Admin','2026-09-24 10:31:00.000000');
INSERT INTO "order_status_history" VALUES(127,32,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-09-22 08:47:00.000000');
INSERT INTO "order_status_history" VALUES(128,32,'PAID','Payment Verified','Payment received and verified.','Store Admin','2026-09-22 09:02:00.000000');
INSERT INTO "order_status_history" VALUES(129,32,'CONFIRMED','Order Confirmed','Order confirmed and assigned for packaging.','Store Admin','2026-09-22 09:07:00.000000');
INSERT INTO "order_status_history" VALUES(130,32,'PACKED','Order Packed','Items inspected and safely packaged in protective bubble wrap.','Store Admin','2026-09-22 09:52:00.000000');
INSERT INTO "order_status_history" VALUES(131,32,'SHIPPED','Order Shipped','Handed over to BlueDart Express. Tracking AWB: BD0032IN','Store Admin','2026-09-22 12:52:00.000000');
INSERT INTO "order_status_history" VALUES(132,32,'DELIVERED','Delivered','Shipment successfully delivered to recipient.','Store Admin','2026-09-24 12:52:00.000000');
INSERT INTO "order_status_history" VALUES(133,33,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-09-20 09:11:00.000000');
INSERT INTO "order_status_history" VALUES(134,33,'PAID','Payment Verified','Payment received and verified.','Store Admin','2026-09-20 09:26:00.000000');
INSERT INTO "order_status_history" VALUES(135,33,'CONFIRMED','Order Confirmed','Order confirmed and assigned for packaging.','Store Admin','2026-09-20 09:31:00.000000');
INSERT INTO "order_status_history" VALUES(136,33,'PACKED','Order Packed','Items inspected and safely packaged in protective bubble wrap.','Store Admin','2026-09-20 10:16:00.000000');
INSERT INTO "order_status_history" VALUES(137,33,'SHIPPED','Order Shipped','Handed over to BlueDart Express. Tracking AWB: BD0033IN','Store Admin','2026-09-20 13:16:00.000000');
INSERT INTO "order_status_history" VALUES(138,33,'DELIVERED','Delivered','Shipment successfully delivered to recipient.','Store Admin','2026-09-22 13:16:00.000000');
INSERT INTO "order_status_history" VALUES(139,34,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-09-20 09:24:00.000000');
INSERT INTO "order_status_history" VALUES(140,34,'PAID','Payment Verified','Payment received and verified.','Store Admin','2026-09-20 09:39:00.000000');
INSERT INTO "order_status_history" VALUES(141,34,'CONFIRMED','Order Confirmed','Order confirmed and assigned for packaging.','Store Admin','2026-09-20 09:44:00.000000');
INSERT INTO "order_status_history" VALUES(142,34,'PACKED','Order Packed','Items inspected and safely packaged in protective bubble wrap.','Store Admin','2026-09-20 10:29:00.000000');
INSERT INTO "order_status_history" VALUES(143,34,'SHIPPED','Order Shipped','Handed over to BlueDart Express. Tracking AWB: BD0034IN','Store Admin','2026-09-20 13:29:00.000000');
INSERT INTO "order_status_history" VALUES(144,34,'DELIVERED','Delivered','Shipment successfully delivered to recipient.','Store Admin','2026-09-22 13:29:00.000000');
INSERT INTO "order_status_history" VALUES(145,35,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-09-18 07:25:00.000000');
INSERT INTO "order_status_history" VALUES(146,35,'PAID','Payment Verified','Payment received and verified.','Store Admin','2026-09-18 07:40:00.000000');
INSERT INTO "order_status_history" VALUES(147,35,'CONFIRMED','Order Confirmed','Order confirmed and assigned for packaging.','Store Admin','2026-09-18 07:45:00.000000');
INSERT INTO "order_status_history" VALUES(148,35,'PACKED','Order Packed','Items inspected and safely packaged in protective bubble wrap.','Store Admin','2026-09-18 08:30:00.000000');
INSERT INTO "order_status_history" VALUES(149,35,'SHIPPED','Order Shipped','Handed over to BlueDart Express. Tracking AWB: BD0035IN','Store Admin','2026-09-18 11:30:00.000000');
INSERT INTO "order_status_history" VALUES(150,35,'DELIVERED','Delivered','Shipment successfully delivered to recipient.','Store Admin','2026-09-20 11:30:00.000000');
INSERT INTO "order_status_history" VALUES(151,36,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-10-04 10:54:26.799412');
INSERT INTO "order_status_history" VALUES(152,36,'PAID','Payment Verified','Payment verified via Manual UPI (UTR: 120392949212).','Store Admin','2026-10-05 10:30:00.000000');
INSERT INTO "order_status_history" VALUES(153,36,'CONFIRMED','Order Confirmed','Order confirmed and queued for fulfillment.','Store Admin','2026-10-05 10:32:00.000000');
INSERT INTO "order_status_history" VALUES(154,36,'PACKED','Order Packed','Tam Dao (SRK) inspected and hand-packaged with IFRA safety seals.','Store Admin','2026-10-05 10:45:00.000000');
INSERT INTO "order_status_history" VALUES(155,36,'SHIPPED','Order Shipped','Handed over to Delhivery Express. AWB: DL928374019IN','Store Admin','2026-10-05 10:50:00.000000');
INSERT INTO "order_status_history" VALUES(156,36,'DELIVERED','Delivered','Shipment successfully delivered to recipient doorstep.','Store Admin','2026-10-05 11:00:00.000000');
INSERT INTO "order_status_history" VALUES(157,4,'PACKED','Order Packed','Items hand-inspected, prepared, and packaged for dispatch.','Store Admin','2026-10-05 05:49:14.379144');
INSERT INTO "order_status_history" VALUES(158,4,'SHIPPED','Order Shipped','Shipment dispatched via Porter (AWB: 12422).','Store Admin','2026-10-05 05:49:34.594977');
INSERT INTO "order_status_history" VALUES(159,4,'DELIVERED','Delivered','Shipment successfully delivered to recipient doorstep.','Store Admin','2026-10-05 05:49:43.816717');
INSERT INTO "order_status_history" VALUES(160,2,'PAID','Payment Verified','Verified by Store Admin','Store Admin','2026-10-05 10:59:21.064222');
INSERT INTO "order_status_history" VALUES(161,2,'CONFIRMED','Order Confirmed','Payment received. Order confirmed and queued for fulfillment.','System','2026-10-05 10:59:21.064222');
INSERT INTO "order_status_history" VALUES(162,2,'PACKED','Order Packed','Items hand-inspected, prepared, and packaged for dispatch.','Store Admin','2026-10-05 10:59:26.312172');
INSERT INTO "order_status_history" VALUES(163,2,'SHIPPED','Order Shipped','Shipment dispatched via Porter (AWB: 242354).','Store Admin','2026-10-05 10:59:55.383796');
INSERT INTO "order_status_history" VALUES(164,2,'DELIVERED','Delivered','Shipment successfully delivered to recipient doorstep.','Store Admin','2026-10-05 10:59:57.685785');
INSERT INTO "order_status_history" VALUES(165,37,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-10-05 11:19:36.015336');
INSERT INTO "order_status_history" VALUES(166,37,'CONFIRMED','Order Confirmed','Order confirmed and queued for fulfillment.','Store Admin','2026-10-05 12:18:39.985273');
INSERT INTO "order_status_history" VALUES(167,37,'PACKED','Order Packed','Items hand-inspected, prepared, and packaged for dispatch.','Store Admin','2026-10-05 12:18:41.914443');
INSERT INTO "order_status_history" VALUES(168,37,'SHIPPED','Order Shipped','Shipment dispatched via Porter (AWB: 756557).','Store Admin','2026-10-05 12:19:38.399792');
INSERT INTO "order_status_history" VALUES(169,38,'PENDING','Order Placed','Order placed by customer via checkout.','Customer','2026-10-05 17:02:34.255633');
INSERT INTO "order_status_history" VALUES(170,38,'PAID','Payment Verified','Verified by Store Admin','Store Admin','2026-10-05 17:06:56.520396');
INSERT INTO "order_status_history" VALUES(171,38,'CONFIRMED','Order Confirmed','Payment received. Order confirmed and queued for fulfillment.','System','2026-10-05 17:06:56.520396');
INSERT INTO "order_status_history" VALUES(172,38,'PACKED','Order Packed','Items hand-inspected, prepared, and packaged for dispatch.','Store Admin','2026-10-05 17:07:03.412314');
INSERT INTO "order_status_history" VALUES(173,38,'SHIPPED','Order Shipped','Shipment dispatched via Porter (AWB: 242354).','Store Admin','2026-10-05 17:07:11.433229');
INSERT INTO "order_status_history" VALUES(174,38,'DELIVERED','Delivered','Shipment successfully delivered to recipient doorstep.','Store Admin','2026-10-05 17:07:12.632400');
INSERT INTO "order_status_history" VALUES(175,37,'DELIVERED','Delivered','Shipment successfully delivered to recipient doorstep.','Store Admin','2026-10-05 17:07:20.429601');
INSERT INTO "order_status_history" VALUES(176,37,'PAID','Payment Verified','Verified by Store Admin','Store Admin','2026-10-05 17:07:21.662321');
CREATE TABLE orders (
	id INTEGER NOT NULL, 
	order_id VARCHAR(32) NOT NULL, 
	customer_id INTEGER NOT NULL, 
	idempotency_token VARCHAR(64), 
	subtotal NUMERIC(10, 2) NOT NULL, 
	delivery_charge NUMERIC(10, 2) NOT NULL, 
	total_amount NUMERIC(10, 2) NOT NULL, 
	order_status VARCHAR(24) NOT NULL, 
	payment_status VARCHAR(24) NOT NULL, 
	payment_method VARCHAR(32) NOT NULL, 
	shipping_name VARCHAR(100) NOT NULL, 
	shipping_phone VARCHAR(15) NOT NULL, 
	shipping_address_line1 VARCHAR(255) NOT NULL, 
	shipping_address_line2 VARCHAR(255), 
	shipping_city VARCHAR(100) NOT NULL, 
	shipping_state VARCHAR(100) NOT NULL, 
	shipping_pincode VARCHAR(10) NOT NULL, 
	notes TEXT, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, payment_verified_at DATETIME, confirmed_at DATETIME, packed_at DATETIME, shipped_at DATETIME, delivered_at DATETIME, cancelled_at DATETIME, courier_name VARCHAR(100), tracking_number VARCHAR(100), tracking_url VARCHAR(255), cancellation_reason VARCHAR(255), 
	PRIMARY KEY (id), 
	FOREIGN KEY(customer_id) REFERENCES customers (id) ON DELETE RESTRICT
);
INSERT INTO "orders" VALUES(1,'PERF-20261001-0001',1,NULL,1298,0,1298,'DELIVERED','PENDING_VERIFICATION','MANUAL_UPI','Rajeev Chouhan','7020651871','Flat 402, Royal Palms, Kothrud',NULL,'Pune','Maharashtra','411038',NULL,'2026-10-01 08:34:00.000000','2026-10-05 05:39:00.328680','2026-10-01 08:49:00.000000','2026-10-01 08:54:00.000000','2026-10-01 09:39:00.000000','2026-10-01 12:39:00.000000','2026-10-03 12:39:00.000000',NULL,'BlueDart Express','BD0001IN',NULL,NULL);
INSERT INTO "orders" VALUES(2,'PERF-20261001-0002',2,NULL,1140,0,1140,'DELIVERED','PAID','COD','Neha Sharma','9893574573','12B, Bandra West, Hill Road',NULL,'Mumbai','Maharashtra','400050','Please call before delivery','2026-10-01 07:54:00.000000','2026-10-05 10:59:57.686644','2026-10-05 10:59:21.064222','2026-10-05 10:59:21.064222','2026-10-05 10:59:26.312172','2026-10-05 10:59:55.383796','2026-10-05 10:59:57.685785',NULL,'Porter','242354',NULL,NULL);
INSERT INTO "orders" VALUES(3,'PERF-20261001-0003',3,NULL,1498,0,1498,'PENDING','PENDING_VERIFICATION','MANUAL_UPI','Tanvi Sharma','9841993858','Plot 18, Road No. 10, Jubilee Hills',NULL,'Hyderabad','Telangana','500033',NULL,'2026-10-01 05:14:00.000000','2026-10-01 05:14:00.000000',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL);
INSERT INTO "orders" VALUES(4,'PERF-20261001-0004',4,NULL,1298,0,1298,'DELIVERED','PAID','MANUAL_UPI','Meera Sharma','9815538051','C-44, Hauz Khas Enclave',NULL,'Delhi','Delhi','110017','Please call before delivery','2026-10-01 10:13:00.000000','2026-10-05 05:49:43.817637','2026-10-01 10:28:00.000000','2026-10-01 10:33:00.000000','2026-10-05 05:49:14.379144','2026-10-05 05:49:34.594977','2026-10-05 05:49:43.816717',NULL,'Porter','12422',NULL,NULL);
INSERT INTO "orders" VALUES(5,'PERF-20261001-0005',5,NULL,1149,0,1149,'CONFIRMED','PAID','COD','Aarav Kapoor','9820123456','77, 100 Feet Road, Indiranagar',NULL,'Bengaluru','Karnataka','560038','Please call before delivery','2026-10-01 04:15:00.000000','2026-10-05 05:39:00.337537','2026-10-01 04:30:00.000000','2026-10-01 04:35:00.000000',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL);
INSERT INTO "orders" VALUES(6,'PERF-20260930-0001',6,NULL,979,50,1029,'PENDING','PENDING_VERIFICATION','MANUAL_UPI','Priya Nair','9847055123','Panampilly Nagar, Main Avenue',NULL,'Kochi','Kerala','682020',NULL,'2026-09-30 08:51:00.000000','2026-09-30 08:51:00.000000',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL);
INSERT INTO "orders" VALUES(7,'PERF-20260930-0002',7,NULL,1298,0,1298,'PACKED','PAID','COD','Aditya Verma','9910456789','Tower 3, DLF Phase 5, Golf Course Road',NULL,'Gurugram','Haryana','122002',NULL,'2026-09-30 04:30:00.000000','2026-10-05 05:39:00.341238','2026-09-30 04:45:00.000000','2026-09-30 04:50:00.000000','2026-09-30 05:35:00.000000',NULL,NULL,NULL,NULL,NULL,NULL,NULL);
INSERT INTO "orders" VALUES(8,'PERF-20260930-0003',8,NULL,1047,0,1047,'PACKED','PAID','MANUAL_UPI','Rohan Deshmukh','9823098765','Civil Lines, Near High Court',NULL,'Nagpur','Maharashtra','440010','Please call before delivery','2026-09-30 07:13:00.000000','2026-10-05 05:39:00.343440','2026-09-30 07:28:00.000000','2026-09-30 07:33:00.000000','2026-09-30 08:18:00.000000',NULL,NULL,NULL,NULL,NULL,NULL,NULL);
INSERT INTO "orders" VALUES(9,'PERF-20260930-0004',9,NULL,1298,0,1298,'CONFIRMED','PAID','MANUAL_UPI','Ananya Sen','9830112233','Ballygunge Circular Road, Flat 3A',NULL,'Kolkata','West Bengal','700019','Please call before delivery','2026-09-30 09:08:00.000000','2026-10-05 05:39:00.345077','2026-09-30 09:23:00.000000','2026-09-30 09:28:00.000000',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL);
INSERT INTO "orders" VALUES(10,'PERF-20260930-0005',10,NULL,380,50,430,'CONFIRMED','PAID','COD','Vikram Singhania','9829033445','C-Scheme, Subhash Marg',NULL,'Jaipur','Rajasthan','302001',NULL,'2026-09-30 03:39:00.000000','2026-10-05 05:39:00.346604','2026-09-30 03:54:00.000000','2026-09-30 03:59:00.000000',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL);
INSERT INTO "orders" VALUES(11,'PERF-20260929-0001',11,NULL,1298,0,1298,'PACKED','PAID','COD','Kavita Rao','9845012398','Lavelle Road, Richmond Town',NULL,'Bengaluru','Karnataka','560001','Please call before delivery','2026-09-29 08:05:00.000000','2026-10-05 05:39:00.348306','2026-09-29 08:20:00.000000','2026-09-29 08:25:00.000000','2026-09-29 09:10:00.000000',NULL,NULL,NULL,NULL,NULL,NULL,NULL);
INSERT INTO "orders" VALUES(12,'PERF-20260929-0002',12,NULL,1298,0,1298,'SHIPPED','PAID','MANUAL_UPI','Zaid Khan','9892019283','Lokhandwala Complex, Andheri West',NULL,'Mumbai','Maharashtra','400053',NULL,'2026-09-29 07:05:00.000000','2026-10-05 05:39:00.350351','2026-09-29 07:20:00.000000','2026-09-29 07:25:00.000000','2026-09-29 08:10:00.000000','2026-09-29 11:10:00.000000',NULL,NULL,'BlueDart Express','BD0012IN',NULL,NULL);
INSERT INTO "orders" VALUES(13,'PERF-20260929-0003',13,NULL,2298,0,2298,'SHIPPED','PAID','COD','Siddharth Jain','9871234567','Bodakdev, SG Highway',NULL,'Ahmedabad','Gujarat','380015',NULL,'2026-09-29 03:23:00.000000','2026-10-05 05:39:00.352135','2026-09-29 03:38:00.000000','2026-09-29 03:43:00.000000','2026-09-29 04:28:00.000000','2026-09-29 07:28:00.000000',NULL,NULL,'BlueDart Express','BD0013IN',NULL,NULL);
INSERT INTO "orders" VALUES(14,'PERF-20260929-0004',14,NULL,1140,0,1140,'CONFIRMED','PAID','MANUAL_UPI','Pooja Malhotra','9811098765','Sector 9-C, Inner Ring Road',NULL,'Chandigarh','Punjab','160009',NULL,'2026-09-29 06:53:00.000000','2026-10-05 05:39:00.353784','2026-09-29 07:08:00.000000','2026-09-29 07:13:00.000000',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL);
INSERT INTO "orders" VALUES(15,'PERF-20260928-0001',15,NULL,1748,0,1748,'SHIPPED','PAID','MANUAL_UPI','Ishaan Roy','9831987654','Southern Avenue, Lake Terrace',NULL,'Kolkata','West Bengal','700029',NULL,'2026-09-28 03:38:00.000000','2026-10-05 05:39:00.355381','2026-09-28 03:53:00.000000','2026-09-28 03:58:00.000000','2026-09-28 04:43:00.000000','2026-09-28 07:43:00.000000',NULL,NULL,'BlueDart Express','BD0015IN',NULL,NULL);
INSERT INTO "orders" VALUES(16,'PERF-20260928-0002',16,NULL,1298,0,1298,'DELIVERED','PAID','COD','Divya Reddy','9849012345','Madhapur, Hitec City Phase 2',NULL,'Hyderabad','Telangana','500081','Please call before delivery','2026-09-28 06:40:00.000000','2026-10-05 05:39:00.358749','2026-09-28 06:55:00.000000','2026-09-28 07:00:00.000000','2026-09-28 07:45:00.000000','2026-09-28 10:45:00.000000','2026-09-30 10:45:00.000000',NULL,'BlueDart Express','BD0016IN',NULL,NULL);
INSERT INTO "orders" VALUES(17,'PERF-20260928-0003',1,NULL,1140,0,1140,'DELIVERED','PAID','MANUAL_UPI','Rajeev Chouhan','7020651871','Flat 402, Royal Palms, Kothrud',NULL,'Pune','Maharashtra','411038',NULL,'2026-09-28 09:43:00.000000','2026-10-05 05:39:00.360881','2026-09-28 09:58:00.000000','2026-09-28 10:03:00.000000','2026-09-28 10:48:00.000000','2026-09-28 13:48:00.000000','2026-09-30 13:48:00.000000',NULL,'BlueDart Express','BD0017IN',NULL,NULL);
INSERT INTO "orders" VALUES(18,'PERF-20260928-0004',2,NULL,1498,0,1498,'PENDING','PENDING_VERIFICATION','MANUAL_UPI','Neha Sharma','9893574573','12B, Bandra West, Hill Road',NULL,'Mumbai','Maharashtra','400050','Please call before delivery','2026-09-28 09:43:00.000000','2026-09-28 09:43:00.000000',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL);
INSERT INTO "orders" VALUES(19,'PERF-20260927-0001',3,NULL,1298,0,1298,'DELIVERED','PAID','MANUAL_UPI','Tanvi Sharma','9841993858','Plot 18, Road No. 10, Jubilee Hills',NULL,'Hyderabad','Telangana','500033',NULL,'2026-09-27 03:25:00.000000','2026-10-05 05:39:00.363438','2026-09-27 03:40:00.000000','2026-09-27 03:45:00.000000','2026-09-27 04:30:00.000000','2026-09-27 07:30:00.000000','2026-09-29 07:30:00.000000',NULL,'BlueDart Express','BD0019IN',NULL,NULL);
INSERT INTO "orders" VALUES(20,'PERF-20260927-0002',4,NULL,1149,0,1149,'SHIPPED','PAID','COD','Meera Sharma','9815538051','C-44, Hauz Khas Enclave',NULL,'Delhi','Delhi','110017','Please call before delivery','2026-09-27 03:13:00.000000','2026-10-05 05:39:00.365149','2026-09-27 03:28:00.000000','2026-09-27 03:33:00.000000','2026-09-27 04:18:00.000000','2026-09-27 07:18:00.000000',NULL,NULL,'BlueDart Express','BD0020IN',NULL,NULL);
INSERT INTO "orders" VALUES(21,'PERF-20260927-0003',5,NULL,979,50,1029,'PACKED','PAID','MANUAL_UPI','Aarav Kapoor','9820123456','77, 100 Feet Road, Indiranagar',NULL,'Bengaluru','Karnataka','560038','Please call before delivery','2026-09-27 09:52:00.000000','2026-10-05 05:39:00.366765','2026-09-27 10:07:00.000000','2026-09-27 10:12:00.000000','2026-09-27 10:57:00.000000',NULL,NULL,NULL,NULL,NULL,NULL,NULL);
INSERT INTO "orders" VALUES(22,'PERF-20260926-0001',6,NULL,1298,0,1298,'DELIVERED','PAID','COD','Priya Nair','9847055123','Panampilly Nagar, Main Avenue',NULL,'Kochi','Kerala','682020',NULL,'2026-09-26 10:20:00.000000','2026-10-05 05:39:00.368433','2026-09-26 10:35:00.000000','2026-09-26 10:40:00.000000','2026-09-26 11:25:00.000000','2026-09-26 14:25:00.000000','2026-09-28 14:25:00.000000',NULL,'BlueDart Express','BD0022IN',NULL,NULL);
INSERT INTO "orders" VALUES(23,'PERF-20260926-0002',7,NULL,1047,0,1047,'DELIVERED','PAID','MANUAL_UPI','Aditya Verma','9910456789','Tower 3, DLF Phase 5, Golf Course Road',NULL,'Gurugram','Haryana','122002','Please call before delivery','2026-09-26 03:13:00.000000','2026-10-05 05:39:00.370185','2026-09-26 03:28:00.000000','2026-09-26 03:33:00.000000','2026-09-26 04:18:00.000000','2026-09-26 07:18:00.000000','2026-09-28 07:18:00.000000',NULL,'BlueDart Express','BD0023IN',NULL,NULL);
INSERT INTO "orders" VALUES(24,'PERF-20260926-0003',8,NULL,1298,0,1298,'CANCELLED','FAILED','COD','Rohan Deshmukh','9823098765','Civil Lines, Near High Court',NULL,'Nagpur','Maharashtra','440010','Please call before delivery','2026-09-26 07:15:00.000000','2026-10-05 05:39:00.372062',NULL,NULL,NULL,NULL,NULL,'2026-09-26 08:15:00.000000',NULL,NULL,NULL,NULL);
INSERT INTO "orders" VALUES(25,'PERF-20260925-0001',9,NULL,380,50,430,'DELIVERED','PAID','MANUAL_UPI','Ananya Sen','9830112233','Ballygunge Circular Road, Flat 3A',NULL,'Kolkata','West Bengal','700019',NULL,'2026-09-25 05:09:00.000000','2026-10-05 05:39:00.375048','2026-09-25 05:24:00.000000','2026-09-25 05:29:00.000000','2026-09-25 06:14:00.000000','2026-09-25 09:14:00.000000','2026-09-27 09:14:00.000000',NULL,'BlueDart Express','BD0025IN',NULL,NULL);
INSERT INTO "orders" VALUES(26,'PERF-20260925-0002',10,NULL,1298,0,1298,'DELIVERED','PAID','COD','Vikram Singhania','9829033445','C-Scheme, Subhash Marg',NULL,'Jaipur','Rajasthan','302001',NULL,'2026-09-25 07:05:00.000000','2026-10-05 05:39:00.377131','2026-09-25 07:20:00.000000','2026-09-25 07:25:00.000000','2026-09-25 08:10:00.000000','2026-09-25 11:10:00.000000','2026-09-27 11:10:00.000000',NULL,'BlueDart Express','BD0026IN',NULL,NULL);
INSERT INTO "orders" VALUES(27,'PERF-20260925-0003',11,NULL,1298,0,1298,'CANCELLED','REFUNDED','MANUAL_UPI','Kavita Rao','9845012398','Lavelle Road, Richmond Town',NULL,'Bengaluru','Karnataka','560001',NULL,'2026-09-25 10:29:00.000000','2026-10-05 05:39:00.378794',NULL,NULL,NULL,NULL,NULL,'2026-09-25 11:29:00.000000',NULL,NULL,NULL,NULL);
INSERT INTO "orders" VALUES(28,'PERF-20260924-0001',12,NULL,2298,0,2298,'DELIVERED','PAID','MANUAL_UPI','Zaid Khan','9892019283','Lokhandwala Complex, Andheri West',NULL,'Mumbai','Maharashtra','400053',NULL,'2026-09-24 10:37:00.000000','2026-10-05 05:39:00.380373','2026-09-24 10:52:00.000000','2026-09-24 10:57:00.000000','2026-09-24 11:42:00.000000','2026-09-24 14:42:00.000000','2026-09-26 14:42:00.000000',NULL,'BlueDart Express','BD0028IN',NULL,NULL);
INSERT INTO "orders" VALUES(29,'PERF-20260924-0002',13,NULL,1140,0,1140,'DELIVERED','PAID','COD','Siddharth Jain','9871234567','Bodakdev, SG Highway',NULL,'Ahmedabad','Gujarat','380015','Please call before delivery','2026-09-24 03:07:00.000000','2026-10-05 05:39:00.382105','2026-09-24 03:22:00.000000','2026-09-24 03:27:00.000000','2026-09-24 04:12:00.000000','2026-09-24 07:12:00.000000','2026-09-26 07:12:00.000000',NULL,'BlueDart Express','BD0029IN',NULL,NULL);
INSERT INTO "orders" VALUES(30,'PERF-20260924-0003',14,NULL,1748,0,1748,'PENDING','PENDING_VERIFICATION','MANUAL_UPI','Pooja Malhotra','9811098765','Sector 9-C, Inner Ring Road',NULL,'Chandigarh','Punjab','160009',NULL,'2026-09-24 09:42:00.000000','2026-09-24 09:42:00.000000',NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL,NULL);
INSERT INTO "orders" VALUES(31,'PERF-20260922-0001',15,NULL,1298,0,1298,'DELIVERED','PAID','MANUAL_UPI','Ishaan Roy','9831987654','Southern Avenue, Lake Terrace',NULL,'Kolkata','West Bengal','700029','Please call before delivery','2026-09-22 06:26:00.000000','2026-10-05 05:39:00.384571','2026-09-22 06:41:00.000000','2026-09-22 06:46:00.000000','2026-09-22 07:31:00.000000','2026-09-22 10:31:00.000000','2026-09-24 10:31:00.000000',NULL,'BlueDart Express','BD0031IN',NULL,NULL);
INSERT INTO "orders" VALUES(32,'PERF-20260922-0002',16,NULL,1140,0,1140,'DELIVERED','PAID','COD','Divya Reddy','9849012345','Madhapur, Hitec City Phase 2',NULL,'Hyderabad','Telangana','500081',NULL,'2026-09-22 08:47:00.000000','2026-10-05 05:39:00.386380','2026-09-22 09:02:00.000000','2026-09-22 09:07:00.000000','2026-09-22 09:52:00.000000','2026-09-22 12:52:00.000000','2026-09-24 12:52:00.000000',NULL,'BlueDart Express','BD0032IN',NULL,NULL);
INSERT INTO "orders" VALUES(33,'PERF-20260920-0001',1,NULL,1498,0,1498,'DELIVERED','PAID','MANUAL_UPI','Rajeev Chouhan','7020651871','Flat 402, Royal Palms, Kothrud',NULL,'Pune','Maharashtra','411038','Please call before delivery','2026-09-20 09:11:00.000000','2026-10-05 05:39:00.388111','2026-09-20 09:26:00.000000','2026-09-20 09:31:00.000000','2026-09-20 10:16:00.000000','2026-09-20 13:16:00.000000','2026-09-22 13:16:00.000000',NULL,'BlueDart Express','BD0033IN',NULL,NULL);
INSERT INTO "orders" VALUES(34,'PERF-20260920-0002',2,NULL,1298,0,1298,'DELIVERED','PAID','COD','Neha Sharma','9893574573','12B, Bandra West, Hill Road',NULL,'Mumbai','Maharashtra','400050',NULL,'2026-09-20 09:24:00.000000','2026-10-05 05:39:00.390805','2026-09-20 09:39:00.000000','2026-09-20 09:44:00.000000','2026-09-20 10:29:00.000000','2026-09-20 13:29:00.000000','2026-09-22 13:29:00.000000',NULL,'BlueDart Express','BD0034IN',NULL,NULL);
INSERT INTO "orders" VALUES(35,'PERF-20260918-0001',3,NULL,1149,0,1149,'DELIVERED','PAID','MANUAL_UPI','Tanvi Sharma','9841993858','Plot 18, Road No. 10, Jubilee Hills',NULL,'Hyderabad','Telangana','500033',NULL,'2026-09-18 07:25:00.000000','2026-10-05 05:39:00.393015','2026-09-18 07:40:00.000000','2026-09-18 07:45:00.000000','2026-09-18 08:30:00.000000','2026-09-18 11:30:00.000000','2026-09-20 11:30:00.000000',NULL,'BlueDart Express','BD0035IN',NULL,NULL);
INSERT INTO "orders" VALUES(36,'PERF-20261004-0001',1,'4ce8bda3-8169-4298-9058-b26e178a896d',380,50,430,'DELIVERED','PAID','MANUAL_UPI','Rajeev chouhan','7020651871','c-303 Raagdari Apartments , Opposite Kaka Halwai , Aundh , 411007','Near westend mall','Pune','Maharastra','411007',NULL,'2026-10-04 10:54:26.799412','2026-10-05 05:39:00.394658','2026-10-05 10:30:00.000000','2026-10-05 10:32:00.000000','2026-10-05 10:45:00.000000','2026-10-05 10:50:00.000000','2026-10-05 11:00:00.000000',NULL,'Delhivery Express','DL928374019IN',NULL,NULL);
INSERT INTO "orders" VALUES(37,'PERF-20261005-0001',1,'f5a58476-9dc6-4dcd-b00a-2a884316f892',380,50,430,'DELIVERED','PAID','MANUAL_UPI','rajeev chouhan','7020651871','c-303 Raagdari Apartments , Opposite Kaka Halwai , Aundh , 411007','Near westend mall','Pune','Maharastra','411007',NULL,'2026-10-05 11:19:36.015336','2026-10-05 17:07:21.663275','2026-10-05 17:07:21.662321','2026-10-05 12:18:39.985273','2026-10-05 12:18:41.914443','2026-10-05 12:19:38.399792','2026-10-05 17:07:20.429601',NULL,'Porter','756557',NULL,NULL);
INSERT INTO "orders" VALUES(38,'PERF-20261005-0002',1,'a693e73a-5a05-4ed1-a6cd-4da2a109244f',649,50,699,'DELIVERED','PAID','MANUAL_UPI','rajeev chouhan','7020651871','c-303 Raagdari Apartments , Opposite Kaka Halwai , Aundh , 411007','Near westend mall','Pune','Maharastra','411007',NULL,'2026-10-05 17:02:34.255633','2026-10-05 17:07:12.633514','2026-10-05 17:06:56.520396','2026-10-05 17:06:56.520396','2026-10-05 17:07:03.412314','2026-10-05 17:07:11.433229','2026-10-05 17:07:12.632400',NULL,'Porter','242354',NULL,NULL);
CREATE TABLE pages (
	id INTEGER NOT NULL, 
	slug VARCHAR(80) NOT NULL, 
	title VARCHAR(150) NOT NULL, 
	content TEXT NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
INSERT INTO "pages" VALUES(1,'about-us','About Scented Bubbles','<p>At <strong>Scented Bubbles</strong>, we believe every space and moment deserves an aura of quiet luxury. Born from a devotion to artisanal perfumery, our creations balance French perfumery heritage with contemporary refinement.</p><p>From long-lasting Eau de Parfums to slow-evaporating wooden car diffusers, every batch of Scented Bubbles is hand-blended with IFRA-compliant fragrance oils, pure essential extracts, and cosmetic-grade carriers.</p>',1,'2026-09-30 14:16:37.347286','2026-09-30 14:16:37.347288');
INSERT INTO "pages" VALUES(2,'shipping-policy','Shipping Policy | Scented Bubbles','<p>Orders placed at <strong>Scented Bubbles</strong> are dispatched within 24 to 48 business hours. We deliver across India with premium courier partners including Blue Dart, Delhivery, and DTDC.</p><p>Standard delivery takes 3 to 6 business days. Free shipping is automatically applied to all orders above ₹999.</p>',1,'2026-09-30 14:16:37.348219','2026-09-30 14:16:37.348221');
INSERT INTO "pages" VALUES(3,'refund-policy','Returns & Refunds | Scented Bubbles','<p>Due to the personal nature of fine fragrances, <strong>Scented Bubbles</strong> cannot accept returns on opened perfume bottles or car diffusers. However, if your package arrives damaged, leaked, or incorrect, please reach out to care@scentedbubbles.com or message us on WhatsApp with an unboxing video within 48 hours for an instant replacement or refund.</p>',1,'2026-09-30 14:16:37.348847','2026-09-30 14:16:37.348849');
INSERT INTO "pages" VALUES(4,'terms-conditions','Terms & Conditions | Scented Bubbles','<p>Welcome to <strong>Scented Bubbles</strong>. By accessing or shopping on our website, you agree to these terms. All products, imagery, and formulas are proprietary to Scented Bubbles. Prices and product availability are subject to change without prior notice.</p>',1,'2026-09-30 14:16:37.349475','2026-09-30 14:16:37.349477');
INSERT INTO "pages" VALUES(5,'privacy-policy','Privacy Policy | Scented Bubbles','<p>Your privacy is paramount at <strong>Scented Bubbles</strong>. We collect customer name, phone number, and delivery address solely for fulfilling orders, tracking packages, and providing customer care. We never sell or lease your personal information to third parties.</p>',1,'2026-09-30 14:16:37.350111','2026-09-30 14:16:37.350113');
CREATE TABLE payments (
	id INTEGER NOT NULL, 
	order_id INTEGER NOT NULL, 
	payment_method VARCHAR(32) NOT NULL, 
	amount NUMERIC(10, 2) NOT NULL, 
	utr VARCHAR(64), 
	status VARCHAR(32) NOT NULL, 
	notes TEXT, 
	raw_response TEXT, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(order_id) REFERENCES orders (id) ON DELETE CASCADE
);
INSERT INTO "payments" VALUES(1,1,'MANUAL_UPI',1298,'UTR261001-098231','PENDING_VERIFICATION','Payment for PERF-20261001-0001',NULL,'2026-10-01 08:34:00.000000','2026-10-01 08:34:00.000000');
INSERT INTO "payments" VALUES(2,2,'COD',1140,NULL,'PAID','Cash on delivery order
Verified by Store Admin',NULL,'2026-10-01 07:54:00.000000','2026-10-05 10:59:21.074731');
INSERT INTO "payments" VALUES(3,3,'MANUAL_UPI',1498,'UTR261001-443190','PENDING_VERIFICATION','Payment for PERF-20261001-0003',NULL,'2026-10-01 05:14:00.000000','2026-10-01 05:14:00.000000');
INSERT INTO "payments" VALUES(4,4,'MANUAL_UPI',1298,'UTR261001-889102','PAID','Payment for PERF-20261001-0004',NULL,'2026-10-01 10:13:00.000000','2026-10-01 10:13:00.000000');
INSERT INTO "payments" VALUES(5,5,'COD',1149,NULL,'PAID','Cash on delivery order',NULL,'2026-10-01 04:15:00.000000','2026-10-01 04:15:00.000000');
INSERT INTO "payments" VALUES(6,6,'MANUAL_UPI',1029,'UTR260930-112345','PENDING_VERIFICATION','Payment for PERF-20260930-0001',NULL,'2026-09-30 08:51:00.000000','2026-09-30 08:51:00.000000');
INSERT INTO "payments" VALUES(7,7,'COD',1298,NULL,'PAID','Cash on delivery order',NULL,'2026-09-30 04:30:00.000000','2026-09-30 04:30:00.000000');
INSERT INTO "payments" VALUES(8,8,'MANUAL_UPI',1047,'UTR260930-554433','PAID','Payment for PERF-20260930-0003',NULL,'2026-09-30 07:13:00.000000','2026-09-30 07:13:00.000000');
INSERT INTO "payments" VALUES(9,9,'MANUAL_UPI',1298,'UTR260930-998877','PAID','Payment for PERF-20260930-0004',NULL,'2026-09-30 09:08:00.000000','2026-09-30 09:08:00.000000');
INSERT INTO "payments" VALUES(10,10,'COD',430,NULL,'PAID','Cash on delivery order
Verified by Store Admin',NULL,'2026-09-30 03:39:00.000000','2026-10-04 10:08:48.064950');
INSERT INTO "payments" VALUES(11,11,'COD',1298,NULL,'PAID','Cash on delivery order',NULL,'2026-09-29 08:05:00.000000','2026-09-29 08:05:00.000000');
INSERT INTO "payments" VALUES(12,12,'MANUAL_UPI',1298,'UTR260929-771122','PAID','Payment for PERF-20260929-0002',NULL,'2026-09-29 07:05:00.000000','2026-09-29 07:05:00.000000');
INSERT INTO "payments" VALUES(13,13,'COD',2298,NULL,'PAID','Cash on delivery order',NULL,'2026-09-29 03:23:00.000000','2026-09-29 03:23:00.000000');
INSERT INTO "payments" VALUES(14,14,'MANUAL_UPI',1140,'UTR260929-338811','PAID','Payment for PERF-20260929-0004',NULL,'2026-09-29 06:53:00.000000','2026-09-29 06:53:00.000000');
INSERT INTO "payments" VALUES(15,15,'MANUAL_UPI',1748,'UTR260928-662244','PAID','Payment for PERF-20260928-0001',NULL,'2026-09-28 03:38:00.000000','2026-09-28 03:38:00.000000');
INSERT INTO "payments" VALUES(16,16,'COD',1298,NULL,'PAID','Cash on delivery order',NULL,'2026-09-28 06:40:00.000000','2026-09-28 06:40:00.000000');
INSERT INTO "payments" VALUES(17,17,'MANUAL_UPI',1140,'UTR260928-883311','PAID','Payment for PERF-20260928-0003',NULL,'2026-09-28 09:43:00.000000','2026-09-28 09:43:00.000000');
INSERT INTO "payments" VALUES(18,18,'MANUAL_UPI',1498,'UTR260928-994422','PENDING_VERIFICATION','Payment for PERF-20260928-0004',NULL,'2026-09-28 09:43:00.000000','2026-09-28 09:43:00.000000');
INSERT INTO "payments" VALUES(19,19,'MANUAL_UPI',1298,'UTR260927-441199','PAID','Payment for PERF-20260927-0001',NULL,'2026-09-27 03:25:00.000000','2026-09-27 03:25:00.000000');
INSERT INTO "payments" VALUES(20,20,'COD',1149,NULL,'PAID','Cash on delivery order',NULL,'2026-09-27 03:13:00.000000','2026-09-27 03:13:00.000000');
INSERT INTO "payments" VALUES(21,21,'MANUAL_UPI',1029,'UTR260927-223388','PAID','Payment for PERF-20260927-0003',NULL,'2026-09-27 09:52:00.000000','2026-09-27 09:52:00.000000');
INSERT INTO "payments" VALUES(22,22,'COD',1298,NULL,'PAID','Cash on delivery order',NULL,'2026-09-26 10:20:00.000000','2026-09-26 10:20:00.000000');
INSERT INTO "payments" VALUES(23,23,'MANUAL_UPI',1047,'UTR260926-778811','PAID','Payment for PERF-20260926-0002',NULL,'2026-09-26 03:13:00.000000','2026-09-26 03:13:00.000000');
INSERT INTO "payments" VALUES(24,24,'COD',1298,NULL,'FAILED','Cash on delivery order',NULL,'2026-09-26 07:15:00.000000','2026-09-26 07:15:00.000000');
INSERT INTO "payments" VALUES(25,25,'MANUAL_UPI',430,'UTR260925-334455','PAID','Payment for PERF-20260925-0001',NULL,'2026-09-25 05:09:00.000000','2026-09-25 05:09:00.000000');
INSERT INTO "payments" VALUES(26,26,'COD',1298,NULL,'PAID','Cash on delivery order',NULL,'2026-09-25 07:05:00.000000','2026-09-25 07:05:00.000000');
INSERT INTO "payments" VALUES(27,27,'MANUAL_UPI',1298,'UTR260925-887766','REFUNDED','Payment for PERF-20260925-0003',NULL,'2026-09-25 10:29:00.000000','2026-09-25 10:29:00.000000');
INSERT INTO "payments" VALUES(28,28,'MANUAL_UPI',2298,'UTR260924-119922','PAID','Payment for PERF-20260924-0001',NULL,'2026-09-24 10:37:00.000000','2026-09-24 10:37:00.000000');
INSERT INTO "payments" VALUES(29,29,'COD',1140,NULL,'PAID','Cash on delivery order',NULL,'2026-09-24 03:07:00.000000','2026-09-24 03:07:00.000000');
INSERT INTO "payments" VALUES(30,30,'MANUAL_UPI',1748,'UTR260924-448833','PENDING_VERIFICATION','Payment for PERF-20260924-0003',NULL,'2026-09-24 09:42:00.000000','2026-09-24 09:42:00.000000');
INSERT INTO "payments" VALUES(31,31,'MANUAL_UPI',1298,'UTR260922-552211','PAID','Payment for PERF-20260922-0001',NULL,'2026-09-22 06:26:00.000000','2026-09-22 06:26:00.000000');
INSERT INTO "payments" VALUES(32,32,'COD',1140,NULL,'PAID','Cash on delivery order',NULL,'2026-09-22 08:47:00.000000','2026-09-22 08:47:00.000000');
INSERT INTO "payments" VALUES(33,33,'MANUAL_UPI',1498,'UTR260920-993311','PAID','Payment for PERF-20260920-0001',NULL,'2026-09-20 09:11:00.000000','2026-09-20 09:11:00.000000');
INSERT INTO "payments" VALUES(34,34,'COD',1298,NULL,'PAID','Cash on delivery order',NULL,'2026-09-20 09:24:00.000000','2026-09-20 09:24:00.000000');
INSERT INTO "payments" VALUES(35,35,'MANUAL_UPI',1149,'UTR260918-114477','PAID','Payment for PERF-20260918-0001',NULL,'2026-09-18 07:25:00.000000','2026-09-18 07:25:00.000000');
INSERT INTO "payments" VALUES(36,36,'MANUAL_UPI',430,'120392949212','PAID','Customer UPI submission awaiting admin verification
Verified by Store Admin',NULL,'2026-10-04 10:54:26.804760','2026-10-05 05:26:33.605794');
INSERT INTO "payments" VALUES(37,37,'MANUAL_UPI',430,'3466y67w2356','PAID','Customer UPI submission awaiting admin verification
Verified by Store Admin',NULL,'2026-10-05 11:19:36.021782','2026-10-05 17:07:21.666401');
INSERT INTO "payments" VALUES(38,38,'MANUAL_UPI',699,NULL,'PAID','Customer UPI submission awaiting admin verification
Verified by Store Admin',NULL,'2026-10-05 17:02:34.258363','2026-10-05 17:06:56.526623');
CREATE TABLE product_categories (
	product_id INTEGER NOT NULL, 
	category_id INTEGER NOT NULL, 
	PRIMARY KEY (product_id, category_id), 
	FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE CASCADE, 
	FOREIGN KEY(category_id) REFERENCES categories (id) ON DELETE CASCADE
);
INSERT INTO "product_categories" VALUES(1,1);
INSERT INTO "product_categories" VALUES(2,1);
INSERT INTO "product_categories" VALUES(3,1);
INSERT INTO "product_categories" VALUES(4,1);
INSERT INTO "product_categories" VALUES(5,1);
INSERT INTO "product_categories" VALUES(6,1);
INSERT INTO "product_categories" VALUES(7,1);
INSERT INTO "product_categories" VALUES(8,1);
INSERT INTO "product_categories" VALUES(9,1);
INSERT INTO "product_categories" VALUES(10,1);
INSERT INTO "product_categories" VALUES(11,1);
INSERT INTO "product_categories" VALUES(12,1);
INSERT INTO "product_categories" VALUES(13,1);
INSERT INTO "product_categories" VALUES(14,1);
INSERT INTO "product_categories" VALUES(15,1);
INSERT INTO "product_categories" VALUES(16,1);
INSERT INTO "product_categories" VALUES(17,1);
INSERT INTO "product_categories" VALUES(18,1);
INSERT INTO "product_categories" VALUES(19,1);
INSERT INTO "product_categories" VALUES(20,1);
INSERT INTO "product_categories" VALUES(21,1);
INSERT INTO "product_categories" VALUES(22,1);
INSERT INTO "product_categories" VALUES(23,1);
INSERT INTO "product_categories" VALUES(24,1);
INSERT INTO "product_categories" VALUES(25,1);
INSERT INTO "product_categories" VALUES(26,1);
INSERT INTO "product_categories" VALUES(27,1);
INSERT INTO "product_categories" VALUES(28,1);
INSERT INTO "product_categories" VALUES(29,1);
INSERT INTO "product_categories" VALUES(30,2);
INSERT INTO "product_categories" VALUES(31,2);
INSERT INTO "product_categories" VALUES(32,2);
INSERT INTO "product_categories" VALUES(33,2);
INSERT INTO "product_categories" VALUES(8,6);
CREATE TABLE product_images (
	id INTEGER NOT NULL, 
	product_id INTEGER NOT NULL, 
	image_key VARCHAR(255) NOT NULL, 
	alt_text VARCHAR(255), 
	display_order INTEGER NOT NULL, 
	is_primary BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE CASCADE
);
INSERT INTO "product_images" VALUES(1,1,'/static/images/perfume_sample.webp','Tam Dao (SRK) Luxury Eau De Parfum bottle',0,1,'2026-10-01 06:43:13.740205');
INSERT INTO "product_images" VALUES(2,2,'/static/images/perfume_sample.webp','Burberry Weekend Luxury Eau De Parfum bottle',0,1,'2026-10-01 06:43:13.743485');
INSERT INTO "product_images" VALUES(3,3,'/static/images/perfume_sample.webp','Azzaro Most Wanted Luxury Eau De Parfum bottle',0,1,'2026-10-01 06:43:13.745238');
INSERT INTO "product_images" VALUES(4,4,'/static/images/perfume_sample.webp','YSL Libre Luxury Eau De Parfum bottle',0,1,'2026-10-01 06:43:13.746950');
INSERT INTO "product_images" VALUES(5,5,'/static/images/perfume_sample.webp','Armani Tobacco Luxury Eau De Parfum bottle',0,1,'2026-10-01 06:43:13.749391');
INSERT INTO "product_images" VALUES(6,6,'/static/images/perfume_sample.webp','Dior Homme Luxury Eau De Parfum bottle',0,1,'2026-10-01 06:43:13.751354');
INSERT INTO "product_images" VALUES(7,7,'/static/images/perfume_sample.webp','Imperial Valley Luxury Eau De Parfum bottle',0,1,'2026-10-01 06:43:13.753210');
INSERT INTO "product_images" VALUES(8,8,'/static/images/perfume_sample.webp','Gucci Guilty Luxury Eau De Parfum bottle',0,1,'2026-10-01 06:43:13.754914');
INSERT INTO "product_images" VALUES(9,9,'/static/images/perfume_sample.webp','CK One Luxury Eau De Parfum bottle',0,1,'2026-10-01 06:43:13.756617');
INSERT INTO "product_images" VALUES(10,10,'/static/images/perfume_sample.webp','Hugo Boss Bottled Luxury Eau De Parfum bottle',0,1,'2026-10-01 06:43:13.758324');
INSERT INTO "product_images" VALUES(11,11,'/static/images/perfume_sample.webp','CR7 (Cristiano Ronaldo) Luxury Eau De Parfum bottle',0,1,'2026-10-01 06:43:13.760014');
INSERT INTO "product_images" VALUES(12,12,'/static/images/perfume_sample.webp','Montblanc Legend Luxury Eau De Parfum bottle',0,1,'2026-10-01 06:43:13.761402');
INSERT INTO "product_images" VALUES(13,13,'/static/images/perfume_sample.webp','Imagination Luxury Eau De Parfum bottle',0,1,'2026-10-01 06:43:13.762744');
INSERT INTO "product_images" VALUES(14,14,'/static/images/perfume_sample.webp','Khamrah Qahwa Luxury Eau De Parfum bottle',0,1,'2026-10-01 06:43:13.764062');
INSERT INTO "product_images" VALUES(15,15,'/static/images/perfume_sample.webp','Astral (FIFA) Luxury Eau De Parfum bottle',0,1,'2026-10-01 06:43:13.766351');
INSERT INTO "product_images" VALUES(16,16,'/static/images/perfume_sample.webp','Aggressive Luxury Eau De Parfum bottle',0,1,'2026-10-01 06:43:13.767949');
INSERT INTO "product_images" VALUES(17,17,'/static/images/perfume_sample.webp','Tom Ford Vanilla Luxury Eau De Parfum bottle',0,1,'2026-10-01 06:43:13.769495');
INSERT INTO "product_images" VALUES(18,18,'/static/images/perfume_sample.webp','Davidoff Cool Water (Akshay Kumar) Luxury Eau De Parfum bottle',0,1,'2026-10-01 06:43:13.770845');
INSERT INTO "product_images" VALUES(19,19,'/static/images/perfume_sample.webp','Club de Nuit Armaf Luxury Eau De Parfum bottle',0,1,'2026-10-01 06:43:13.772164');
INSERT INTO "product_images" VALUES(20,20,'/static/images/perfume_sample.webp','Carolina Herrera - Good Girl Luxury Eau De Parfum bottle',0,1,'2026-10-01 06:43:13.773494');
INSERT INTO "product_images" VALUES(21,21,'/static/images/perfume_sample.webp','Dubai Gold Luxury Eau De Parfum bottle',0,1,'2026-10-01 06:43:13.774825');
INSERT INTO "product_images" VALUES(22,22,'/static/images/perfume_sample.webp','Roja Mischief (Hardik Pandya) Luxury Eau De Parfum bottle',0,1,'2026-10-01 06:43:13.776140');
INSERT INTO "product_images" VALUES(23,23,'/static/images/perfume_sample.webp','Creed Silver Mountain (Shahid Kapoor/ Virat Kohli) Luxury Eau De Parfum bottle',0,1,'2026-10-01 06:43:13.777466');
INSERT INTO "product_images" VALUES(24,24,'/static/images/perfume_sample.webp','Zara Unisex Luxury Eau De Parfum bottle',0,1,'2026-10-01 06:43:13.778810');
INSERT INTO "product_images" VALUES(25,25,'/static/images/perfume_sample.webp','Invictus Luxury Eau De Parfum bottle',0,1,'2026-10-01 06:43:13.780191');
INSERT INTO "product_images" VALUES(26,26,'/static/images/perfume_sample.webp','Versace Eros Luxury Eau De Parfum bottle',0,1,'2026-10-01 06:43:13.781763');
INSERT INTO "product_images" VALUES(27,27,'/static/images/perfume_sample.webp','Men in Black Luxury Eau De Parfum bottle',0,1,'2026-10-01 06:43:13.786234');
INSERT INTO "product_images" VALUES(28,28,'/static/images/perfume_sample.webp','YSL Mon Paris Luxury Eau De Parfum bottle',0,1,'2026-10-01 06:43:13.787632');
INSERT INTO "product_images" VALUES(29,29,'/static/images/perfume_sample.webp','Balmain Paris Luxury Eau De Parfum bottle',0,1,'2026-10-01 06:43:13.788975');
INSERT INTO "product_images" VALUES(30,30,'/static/images/car_sample.webp','Amber Noir Luxury Car Diffuser Luxury Wooden Car Diffuser',0,1,'2026-10-01 06:43:13.790715');
INSERT INTO "product_images" VALUES(31,31,'/static/images/car_sample.webp','Citrus Velvet Luxury Car Diffuser Luxury Wooden Car Diffuser',0,1,'2026-10-01 06:43:13.792036');
INSERT INTO "product_images" VALUES(32,32,'/static/images/car_sample.webp','Royal Oud & Woods Luxury Car Diffuser Luxury Wooden Car Diffuser',0,1,'2026-10-01 06:43:13.793369');
INSERT INTO "product_images" VALUES(33,33,'/static/images/car_sample.webp','Aqua Marine Breeze Luxury Car Diffuser Luxury Wooden Car Diffuser',0,1,'2026-10-01 06:43:13.794692');
INSERT INTO "product_images" VALUES(34,33,'prod_20261001_123401_WhatsApp_Image_2026-10-0_88333b_medium.webp','Aqua Marine Breeze Luxury Car Diffuser image',1,0,'2026-10-01 07:04:01.564726');
CREATE TABLE product_variants (
	id INTEGER NOT NULL, 
	product_id INTEGER NOT NULL, 
	size_label VARCHAR(50) NOT NULL, 
	sku VARCHAR(64) NOT NULL, 
	price NUMERIC(10, 2) NOT NULL, 
	discounted_price NUMERIC(10, 2), 
	stock INTEGER NOT NULL, 
	display_order INTEGER NOT NULL, 
	active BOOLEAN NOT NULL, 
	is_deleted BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(product_id) REFERENCES products (id) ON DELETE CASCADE
);
INSERT INTO "product_variants" VALUES(1,1,'30ml EDP','TAM-DAO--30ML',499,380,49,0,1,0,'2026-10-01 06:43:13.741419','2026-10-04 10:54:26.789824');
INSERT INTO "product_variants" VALUES(2,1,'50ml EDP','TAM-DAO--50ML',799,649,45,1,1,0,'2026-10-01 06:43:13.742214','2026-10-01 06:43:13.742217');
INSERT INTO "product_variants" VALUES(3,1,'100ml EDP','TAM-DAO--100ML',1399,1149,0,2,1,0,'2026-10-01 06:43:13.742603','2026-10-06 07:08:56.784294');
INSERT INTO "product_variants" VALUES(4,2,'30ml EDP','BURBERRY-30ML',499,380,50,0,1,0,'2026-10-01 06:43:13.743631','2026-10-01 06:43:13.743633');
INSERT INTO "product_variants" VALUES(5,2,'50ml EDP','BURBERRY-50ML',799,649,45,1,1,0,'2026-10-01 06:43:13.744030','2026-10-01 06:43:13.744031');
INSERT INTO "product_variants" VALUES(6,2,'100ml EDP','BURBERRY-100ML',1399,1149,10,2,1,0,'2026-10-01 06:43:13.744410','2026-10-05 11:02:32.690717');
INSERT INTO "product_variants" VALUES(7,3,'30ml EDP','AZZARO-M-30ML',499,380,50,0,1,0,'2026-10-01 06:43:13.745384','2026-10-01 06:43:13.745386');
INSERT INTO "product_variants" VALUES(8,3,'50ml EDP','AZZARO-M-50ML',799,649,45,1,1,0,'2026-10-01 06:43:13.745771','2026-10-01 06:43:13.745774');
INSERT INTO "product_variants" VALUES(9,3,'100ml EDP','AZZARO-M-100ML',1399,1149,30,2,1,0,'2026-10-01 06:43:13.746130','2026-10-01 06:43:13.746132');
INSERT INTO "product_variants" VALUES(10,4,'30ml EDP','YSL-LIBR-30ML',499,380,50,0,1,0,'2026-10-01 06:43:13.747093','2026-10-01 06:43:13.747095');
INSERT INTO "product_variants" VALUES(11,4,'50ml EDP','YSL-LIBR-50ML',799,649,45,1,1,0,'2026-10-01 06:43:13.747477','2026-10-01 06:43:13.747479');
INSERT INTO "product_variants" VALUES(12,4,'100ml EDP','YSL-LIBR-100ML',1399,1149,30,2,1,0,'2026-10-01 06:43:13.747916','2026-10-01 06:43:13.747918');
INSERT INTO "product_variants" VALUES(13,5,'30ml EDP','ARMANI-T-30ML',499,380,50,0,1,0,'2026-10-01 06:43:13.749586','2026-10-01 06:43:13.749588');
INSERT INTO "product_variants" VALUES(14,5,'50ml EDP','ARMANI-T-50ML',799,649,45,1,1,0,'2026-10-01 06:43:13.750040','2026-10-01 06:43:13.750042');
INSERT INTO "product_variants" VALUES(15,5,'100ml EDP','ARMANI-T-100ML',1399,1149,30,2,1,0,'2026-10-01 06:43:13.750435','2026-10-01 06:43:13.750437');
INSERT INTO "product_variants" VALUES(16,6,'30ml EDP','DIOR-HOM-30ML',499,380,49,0,1,0,'2026-10-01 06:43:13.751514','2026-10-05 11:19:36.009056');
INSERT INTO "product_variants" VALUES(17,6,'50ml EDP','DIOR-HOM-50ML',799,649,45,1,1,0,'2026-10-01 06:43:13.751903','2026-10-01 06:43:13.751904');
INSERT INTO "product_variants" VALUES(18,6,'100ml EDP','DIOR-HOM-100ML',1399,1149,30,2,1,0,'2026-10-01 06:43:13.752271','2026-10-01 06:43:13.752272');
INSERT INTO "product_variants" VALUES(19,7,'30ml EDP','IMPERIAL-30ML',499,380,50,0,1,0,'2026-10-01 06:43:13.753356','2026-10-01 06:43:13.753357');
INSERT INTO "product_variants" VALUES(20,7,'50ml EDP','IMPERIAL-50ML',799,649,45,1,1,0,'2026-10-01 06:43:13.753741','2026-10-01 06:43:13.753743');
INSERT INTO "product_variants" VALUES(21,7,'100ml EDP','IMPERIAL-100ML',1399,1149,30,2,1,0,'2026-10-01 06:43:13.754097','2026-10-01 06:43:13.754099');
INSERT INTO "product_variants" VALUES(22,8,'30ml EDP','GUCCI-GU-30ML',499,380,50,0,1,0,'2026-10-01 06:43:13.755057','2026-10-01 06:43:13.755058');
INSERT INTO "product_variants" VALUES(23,8,'50ml EDP','GUCCI-GU-50ML',799,649,45,1,1,0,'2026-10-01 06:43:13.755442','2026-10-01 06:43:13.755444');
INSERT INTO "product_variants" VALUES(24,8,'100ml EDP','GUCCI-GU-100ML',1399,1149,30,2,1,0,'2026-10-01 06:43:13.755799','2026-10-01 06:43:13.755801');
INSERT INTO "product_variants" VALUES(25,9,'30ml EDP','CK-ONE-30ML',499,380,50,0,1,0,'2026-10-01 06:43:13.756771','2026-10-01 06:43:13.756773');
INSERT INTO "product_variants" VALUES(26,9,'50ml EDP','CK-ONE-50ML',799,649,45,1,1,0,'2026-10-01 06:43:13.757155','2026-10-01 06:43:13.757156');
INSERT INTO "product_variants" VALUES(27,9,'100ml EDP','CK-ONE-100ML',1399,1149,30,2,1,0,'2026-10-01 06:43:13.757511','2026-10-01 06:43:13.757513');
INSERT INTO "product_variants" VALUES(28,10,'30ml EDP','HUGO-BOS-30ML',499,380,50,0,1,0,'2026-10-01 06:43:13.758471','2026-10-01 06:43:13.758473');
INSERT INTO "product_variants" VALUES(29,10,'50ml EDP','HUGO-BOS-50ML',799,649,45,1,1,0,'2026-10-01 06:43:13.758855','2026-10-01 06:43:13.758857');
INSERT INTO "product_variants" VALUES(30,10,'100ml EDP','HUGO-BOS-100ML',1399,1149,30,2,1,0,'2026-10-01 06:43:13.759211','2026-10-01 06:43:13.759213');
INSERT INTO "product_variants" VALUES(31,11,'50ml EDP','CR7-CRIS-50ML',799,649,45,0,1,0,'2026-10-01 06:43:13.760162','2026-10-01 06:43:13.760164');
INSERT INTO "product_variants" VALUES(32,11,'100ml EDP','CR7-CRIS-100ML',1399,1149,30,1,1,0,'2026-10-01 06:43:13.760560','2026-10-01 06:43:13.760562');
INSERT INTO "product_variants" VALUES(33,12,'50ml EDP','MONTBLAN-50ML',799,649,45,0,1,0,'2026-10-01 06:43:13.761544','2026-10-01 06:43:13.761546');
INSERT INTO "product_variants" VALUES(34,12,'100ml EDP','MONTBLAN-100ML',1399,1149,30,1,1,0,'2026-10-01 06:43:13.761928','2026-10-01 06:43:13.761930');
INSERT INTO "product_variants" VALUES(35,13,'50ml EDP','IMAGINAT-50ML',799,649,45,0,1,0,'2026-10-01 06:43:13.762886','2026-10-01 06:43:13.762888');
INSERT INTO "product_variants" VALUES(36,13,'100ml EDP','IMAGINAT-100ML',1399,1149,30,1,1,0,'2026-10-01 06:43:13.763270','2026-10-01 06:43:13.763272');
INSERT INTO "product_variants" VALUES(37,14,'50ml EDP','KHAMRAH--50ML',799,649,45,0,1,0,'2026-10-01 06:43:13.764210','2026-10-01 06:43:13.764212');
INSERT INTO "product_variants" VALUES(38,14,'100ml EDP','KHAMRAH--100ML',1399,1149,30,1,1,0,'2026-10-01 06:43:13.764690','2026-10-01 06:43:13.764693');
INSERT INTO "product_variants" VALUES(39,15,'50ml EDP','ASTRAL-F-50ML',799,649,45,0,1,0,'2026-10-01 06:43:13.766615','2026-10-01 06:43:13.766617');
INSERT INTO "product_variants" VALUES(40,15,'100ml EDP','ASTRAL-F-100ML',1399,1149,30,1,1,0,'2026-10-01 06:43:13.767049','2026-10-01 06:43:13.767051');
INSERT INTO "product_variants" VALUES(41,16,'50ml EDP','AGGRESSI-50ML',799,649,45,0,1,0,'2026-10-01 06:43:13.768138','2026-10-01 06:43:13.768140');
INSERT INTO "product_variants" VALUES(42,16,'100ml EDP','AGGRESSI-100ML',1399,1149,30,1,1,0,'2026-10-01 06:43:13.768610','2026-10-01 06:43:13.768612');
INSERT INTO "product_variants" VALUES(43,17,'50ml EDP','TOM-FORD-50ML',799,649,45,0,1,0,'2026-10-01 06:43:13.769642','2026-10-01 06:43:13.769644');
INSERT INTO "product_variants" VALUES(44,17,'100ml EDP','TOM-FORD-100ML',1399,1149,30,1,1,0,'2026-10-01 06:43:13.770029','2026-10-01 06:43:13.770031');
INSERT INTO "product_variants" VALUES(45,18,'50ml EDP','DAVIDOFF-50ML',799,649,45,0,1,0,'2026-10-01 06:43:13.770988','2026-10-01 06:43:13.770990');
INSERT INTO "product_variants" VALUES(46,18,'100ml EDP','DAVIDOFF-100ML',1399,1149,30,1,1,0,'2026-10-01 06:43:13.771365','2026-10-01 06:43:13.771367');
INSERT INTO "product_variants" VALUES(47,19,'50ml EDP','CLUB-DE--50ML',799,649,45,0,1,0,'2026-10-01 06:43:13.772318','2026-10-01 06:43:13.772319');
INSERT INTO "product_variants" VALUES(48,19,'100ml EDP','CLUB-DE--100ML',1399,1149,30,1,1,0,'2026-10-01 06:43:13.772697','2026-10-01 06:43:13.772699');
INSERT INTO "product_variants" VALUES(49,20,'50ml EDP','CAROLINA-50ML',799,649,45,0,1,0,'2026-10-01 06:43:13.773635','2026-10-01 06:43:13.773637');
INSERT INTO "product_variants" VALUES(50,20,'100ml EDP','CAROLINA-100ML',1399,1149,30,1,1,0,'2026-10-01 06:43:13.774017','2026-10-01 06:43:13.774018');
INSERT INTO "product_variants" VALUES(51,21,'50ml EDP','DUBAI-GO-50ML',799,649,45,0,1,0,'2026-10-01 06:43:13.774967','2026-10-01 06:43:13.774969');
INSERT INTO "product_variants" VALUES(52,21,'100ml EDP','DUBAI-GO-100ML',1399,1149,30,1,1,0,'2026-10-01 06:43:13.775345','2026-10-01 06:43:13.775347');
INSERT INTO "product_variants" VALUES(53,22,'50ml EDP','ROJA-MIS-50ML',799,649,45,0,1,0,'2026-10-01 06:43:13.776290','2026-10-01 06:43:13.776292');
INSERT INTO "product_variants" VALUES(54,22,'100ml EDP','ROJA-MIS-100ML',1399,1149,30,1,1,0,'2026-10-01 06:43:13.776672','2026-10-01 06:43:13.776674');
INSERT INTO "product_variants" VALUES(55,23,'50ml EDP','CREED-SI-50ML',799,649,45,0,1,0,'2026-10-01 06:43:13.777609','2026-10-01 06:43:13.777610');
INSERT INTO "product_variants" VALUES(56,23,'100ml EDP','CREED-SI-100ML',1399,1149,30,1,1,0,'2026-10-01 06:43:13.777986','2026-10-01 06:43:13.777988');
INSERT INTO "product_variants" VALUES(57,24,'50ml EDP','ZARA-UNI-50ML',799,649,45,0,1,0,'2026-10-01 06:43:13.779001','2026-10-01 06:43:13.779003');
INSERT INTO "product_variants" VALUES(58,24,'100ml EDP','ZARA-UNI-100ML',1399,1149,30,1,1,0,'2026-10-01 06:43:13.779387','2026-10-01 06:43:13.779388');
INSERT INTO "product_variants" VALUES(59,25,'50ml EDP','INVICTUS-50ML',799,649,45,0,1,0,'2026-10-01 06:43:13.780348','2026-10-01 06:43:13.780349');
INSERT INTO "product_variants" VALUES(60,25,'100ml EDP','INVICTUS-100ML',1399,1149,30,1,1,0,'2026-10-01 06:43:13.780728','2026-10-01 06:43:13.780729');
INSERT INTO "product_variants" VALUES(61,26,'50ml EDP','VERSACE--50ML',799,649,45,0,1,0,'2026-10-01 06:43:13.782028','2026-10-01 06:43:13.782031');
INSERT INTO "product_variants" VALUES(62,26,'100ml EDP','VERSACE--100ML',1399,1149,30,1,1,0,'2026-10-01 06:43:13.783071','2026-10-01 06:43:13.783076');
INSERT INTO "product_variants" VALUES(63,27,'50ml EDP','MEN-IN-B-50ML',799,649,45,0,1,0,'2026-10-01 06:43:13.786410','2026-10-01 06:43:13.786412');
INSERT INTO "product_variants" VALUES(64,27,'100ml EDP','MEN-IN-B-100ML',1399,1149,30,1,1,0,'2026-10-01 06:43:13.786806','2026-10-01 06:43:13.786808');
INSERT INTO "product_variants" VALUES(65,28,'50ml EDP','YSL-MON--50ML',799,649,44,0,1,0,'2026-10-01 06:43:13.787777','2026-10-05 17:02:34.247319');
INSERT INTO "product_variants" VALUES(66,28,'100ml EDP','YSL-MON--100ML',1399,1149,30,1,1,0,'2026-10-01 06:43:13.788156','2026-10-01 06:43:13.788159');
INSERT INTO "product_variants" VALUES(67,29,'50ml EDP','BALMAIN--50ML',799,649,45,0,1,0,'2026-10-01 06:43:13.789119','2026-10-01 06:43:13.789121');
INSERT INTO "product_variants" VALUES(68,29,'100ml EDP','BALMAIN--100ML',1399,1149,30,1,1,0,'2026-10-01 06:43:13.789497','2026-10-01 06:43:13.789499');
INSERT INTO "product_variants" VALUES(69,30,'10ml Hanging Diffuser','CAR-AMBER--10ML',399,349,60,0,1,0,'2026-10-01 06:43:13.790857','2026-10-01 06:43:13.790858');
INSERT INTO "product_variants" VALUES(70,30,'Twin Pack (2 x 10ml)','CAR-AMBER--20ML',699,599,40,1,1,0,'2026-10-01 06:43:13.791237','2026-10-01 06:43:13.791239');
INSERT INTO "product_variants" VALUES(71,31,'10ml Hanging Diffuser','CAR-CITRUS-10ML',399,349,60,0,1,0,'2026-10-01 06:43:13.792182','2026-10-01 06:43:13.792183');
INSERT INTO "product_variants" VALUES(72,31,'Twin Pack (2 x 10ml)','CAR-CITRUS-20ML',699,599,40,1,1,0,'2026-10-01 06:43:13.792574','2026-10-01 06:43:13.792576');
INSERT INTO "product_variants" VALUES(73,32,'10ml Hanging Diffuser','CAR-ROYAL--10ML',399,349,60,0,1,0,'2026-10-01 06:43:13.793510','2026-10-01 06:43:13.793511');
INSERT INTO "product_variants" VALUES(74,32,'Twin Pack (2 x 10ml)','CAR-ROYAL--20ML',699,599,40,1,1,0,'2026-10-01 06:43:13.793885','2026-10-01 06:43:13.793886');
INSERT INTO "product_variants" VALUES(75,33,'10ml Hanging Diffuser','CAR-AQUA-M-10ML',399,349,60,0,1,0,'2026-10-01 06:43:13.794834','2026-10-01 06:43:13.794836');
INSERT INTO "product_variants" VALUES(76,33,'Twin Pack (2 x 10ml)','CAR-AQUA-M-20ML',699,599,40,1,1,0,'2026-10-01 06:43:13.795261','2026-10-01 06:43:13.795262');
CREATE TABLE products (
	id INTEGER NOT NULL, 
	category_id INTEGER NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	slug VARCHAR(160) NOT NULL, 
	short_description VARCHAR(255), 
	full_description TEXT, 
	fragrance_family VARCHAR(80), 
	top_notes VARCHAR(255), 
	heart_notes VARCHAR(255), 
	base_notes VARCHAR(255), 
	usage_instructions TEXT, 
	active BOOLEAN NOT NULL, 
	featured BOOLEAN NOT NULL, 
	bestseller BOOLEAN NOT NULL, 
	is_deleted BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, inspired_by VARCHAR(150), 
	PRIMARY KEY (id), 
	FOREIGN KEY(category_id) REFERENCES categories (id) ON DELETE RESTRICT
);
INSERT INTO "products" VALUES(1,1,'Tam Dao (SRK)','tam-dao-srk','Original Manufacturer oil made only perfume inspired by Tam Dao (signature scent of Shah Rukh Khan).','Original Manufacturer oil made only perfume inspired by Tam Dao, famously worn by Shah Rukh Khan. A masterclass in warmth and understated majesty, balancing sacred Goa sandalwood, crisp Italian cypress, and creamy white amber.','Woody Sandalwood','Italian Cypress, Myrtle, Delicate Rose','Goa Sandalwood, Atlas Cedarwood','Golden Amber, White Musk, Brazilian Rosewood','Spritz 2-3 sprays on pulse points: collarbones, wrists, and behind the ears for all-day sillage.',1,1,1,0,'2026-10-01 06:43:13.726980','2026-10-01 06:43:13.726983','Tam Dao (signature scent of Shah Rukh Khan)');
INSERT INTO "products" VALUES(2,1,'Burberry Weekend','burberry-weekend','Original Manufacturer oil made only perfume inspired by Burberry Weekend.','Original Manufacturer oil made only perfume inspired by Burberry Weekend. Relaxing, luminous, and uplifting with sparkling mandarin, sweet nectarine, wild rose, and soft cedarwood.','Fresh Citrus Floral','Mandarin Orange, Sage, Reseda','Blue Hyacinth, Iris, Nectarine, Peach Blossom','Cedarwood, Sandalwood, Sheer Musk','Spritz 2-3 sprays on pulse points: collarbones, wrists, and behind the ears for all-day sillage.',1,1,0,0,'2026-10-01 06:43:13.743040','2026-10-01 06:43:13.743042','Burberry Weekend');
INSERT INTO "products" VALUES(3,1,'Azzaro Most Wanted','azzaro-most-wanted','Original Manufacturer oil made only perfume inspired by Azzaro The Most Wanted.','Original Manufacturer oil made only perfume inspired by Azzaro The Most Wanted. An ultra-addictive, magnetic oriental fragrance featuring fiery cardamom, decadent toffee caramel, and smoky bourbon vanilla.','Amber Woody Gourmand','Guatemalan Cardamom, Mandarin','Toffee Caramel, Provence Lavender','Bourbon Vanilla, Amberwood','Spritz 2-3 sprays on pulse points: collarbones, wrists, and behind the ears for all-day sillage.',1,1,1,0,'2026-10-01 06:43:13.744809','2026-10-01 06:43:13.744811','Azzaro The Most Wanted');
INSERT INTO "products" VALUES(4,1,'YSL Libre','ysl-libre','Original Manufacturer oil made only perfume inspired by YSL Libre.','Original Manufacturer oil made only perfume inspired by YSL Libre. A bold declaration of freedom uniting burning Moroccan orange blossom, crisp French lavender, and glowing Madagascar vanilla.','Floral Lavender','French Diva Lavender, Mandarin, Blackcurrant','Moroccan Orange Blossom, Jasmine Sambac','Madagascar Vanilla, Cedarwood, Ambergris','Spritz 2-3 sprays on pulse points: collarbones, wrists, and behind the ears for all-day sillage.',1,1,1,0,'2026-10-01 06:43:13.746534','2026-10-01 06:43:13.746536','YSL Libre');
INSERT INTO "products" VALUES(5,1,'Armani Tobacco','armani-tobacco','Original Manufacturer oil made only perfume inspired by Armani Privé Tobacco.','Original Manufacturer oil made only perfume inspired by Armani Privé Tobacco. An aristocratic, intoxicating blend of rich aromatic pipe tobacco, sweet dried fruits, honey, and warm oriental resins.','Oriental Tobacco','Spicy Ginger, Blonde Tobacco Leaf, Osmanthus','Golden Honey, Dried Fruits, Clove','Tonka Bean, Bourbon Vanilla, Benzoin Resins','Spritz 2-3 sprays on pulse points: collarbones, wrists, and behind the ears for all-day sillage.',1,0,1,0,'2026-10-01 06:43:13.748431','2026-10-01 06:43:13.748434','Armani Privé Tobacco');
INSERT INTO "products" VALUES(6,1,'Dior Homme','dior-homme','Original Manufacturer oil made only perfume inspired by Dior Homme.','Original Manufacturer oil made only perfume inspired by Dior Homme. Sophisticated masculine elegance defined by noble Tuscan iris, warm cocoa, pink pepper, and Virginia cedarwood.','Woody Floral Musk','Bergamot, Pink Pepper, Elemi','Tuscan Iris, Cashmere Wood, Atlas Cedar','Haitian Vetiver, White Musk, Iso E Super','Spritz 2-3 sprays on pulse points: collarbones, wrists, and behind the ears for all-day sillage.',1,1,0,0,'2026-10-01 06:43:13.750889','2026-10-01 06:43:13.750892','Dior Homme');
INSERT INTO "products" VALUES(7,1,'Imperial Valley','imperial-valley','Original Manufacturer oil made only perfume inspired by Gissah Imperial Valley.','Original Manufacturer oil made only perfume inspired by Gissah Imperial Valley. Regal and commanding, blending rare Davana herbs, Italian bergamot, pink pepper, rosemary, and Cambodian agarwood.','Oriental Aromatic','Davana, Italian Bergamot, Pink Pepper','Rosemary, White Amber, Smoky Agarwood','Leather Accord, Vetiver, Musk','Spritz 2-3 sprays on pulse points: collarbones, wrists, and behind the ears for all-day sillage.',1,1,1,0,'2026-10-01 06:43:13.752677','2026-10-01 06:43:13.752680','Gissah Imperial Valley');
INSERT INTO "products" VALUES(8,1,'Gucci Guilty','gucci-guilty','Original Manufacturer oil made only perfume inspired by Gucci Guilty.','Original Manufacturer oil made only perfume inspired by Gucci Guilty. An alluring, fearless fragrance of sparkling pink pepper, lilac petals, patchouli, and sensual golden amber.',NULL,NULL,NULL,NULL,'Spritz 2-3 sprays on pulse points: collarbones, wrists, and behind the ears for all-day sillage.',1,0,1,0,'2026-10-01 06:43:13.754501','2026-10-06 08:43:48.913563','Gucci Guilty');
INSERT INTO "products" VALUES(9,1,'CK One','ck-one','Original Manufacturer oil made only perfume inspired by CK One.','Original Manufacturer oil made only perfume inspired by CK One. The quintessential clean, universal scent featuring green tea, papaya, bergamot, and sheer skin musk.','Citrus Aromatic','Lemon, Green Notes, Bergamot, Pineapple, Papaya','Lily-of-the-Valley, Jasmine, Violet, Nutmeg','Green Tea, Musk, Cedar, Sandalwood, Oakmoss','Spritz 2-3 sprays on pulse points: collarbones, wrists, and behind the ears for all-day sillage.',1,0,0,0,'2026-10-01 06:43:13.756200','2026-10-01 06:43:13.756202','CK One');
INSERT INTO "products" VALUES(10,1,'Hugo Boss Bottled','hugo-boss-bottled','Original Manufacturer oil made only perfume inspired by Hugo Boss Bottled.','Original Manufacturer oil made only perfume inspired by Hugo Boss Bottled. Crisp red apple, warm cinnamon spice, geranium, and rich sandalwood crafted for the driven modern man.','Woody Spicy','Crisp Apple, Plum, Bergamot, Lemon','Cinnamon, Mahogany Wood, Carnation, Geranium','Vanilla, Sandalwood, Cedar, Vetiver','Spritz 2-3 sprays on pulse points: collarbones, wrists, and behind the ears for all-day sillage.',1,1,1,0,'2026-10-01 06:43:13.757899','2026-10-01 06:43:13.757901','Hugo Boss Bottled');
INSERT INTO "products" VALUES(11,1,'CR7 (Cristiano Ronaldo)','cr7-cristiano-ronaldo','Original Manufacturer oil made only perfume inspired by CR7 (Cristiano Ronaldo). Made in 50ml & 100ml.','Original Manufacturer oil made only perfume inspired by CR7 (Cristiano Ronaldo). An energetic, charismatic fragrance with bold cardamom, fresh lavender, warm cinnamon, and smoky cedarwood.','Aromatic Fougere','Bergamot, Artemisia, Cardamom, Lavender','Cinnamon, Cedarwood, Iris, Tobacco','Sandalwood, Amber, Vanilla, Musk','Spritz 2-3 sprays on pulse points: collarbones, wrists, and behind the ears for all-day sillage.',1,1,1,0,'2026-10-01 06:43:13.759599','2026-10-01 06:43:13.759600','CR7 (Cristiano Ronaldo)');
INSERT INTO "products" VALUES(12,1,'Montblanc Legend','montblanc-legend','Original Manufacturer oil made only perfume inspired by Montblanc Legend.','Original Manufacturer oil made only perfume inspired by Montblanc Legend. Classic charisma blending fresh bergamot, French lavender, pineapple leaf, and exotic sandalwood.','Aromatic Fougere','Lavender, Pineapple, Bergamot, Lemon Verbena','Red Apple, Dried Fruits, Oakmoss, Geranium','Tonka Bean, Sandalwood','Spritz 2-3 sprays on pulse points: collarbones, wrists, and behind the ears for all-day sillage.',1,0,1,0,'2026-10-01 06:43:13.760987','2026-10-01 06:43:13.760989','Montblanc Legend');
INSERT INTO "products" VALUES(13,1,'Imagination','imagination','Original Manufacturer oil made only perfume inspired by Louis Vuitton Imagination.','Original Manufacturer oil made only perfume inspired by Louis Vuitton Imagination. An exhilarating trail of rare Chinese black tea, Sicilian citrus, and radiant ambroxan.','Citrus Aromatic','Calabrian Bergamot, Sicilian Orange, Citron','Ceylon Black Tea, Tunisian Neroli, Nigerian Ginger','Ambroxan, Olibanum, Guaiac Wood','Spritz 2-3 sprays on pulse points: collarbones, wrists, and behind the ears for all-day sillage.',1,1,1,0,'2026-10-01 06:43:13.762330','2026-10-01 06:43:13.762332','Louis Vuitton Imagination');
INSERT INTO "products" VALUES(14,1,'Khamrah Qahwa','khamrah-qahwa','Original Manufacturer oil made only perfume inspired by Lattafa Khamrah Qahwa.','Original Manufacturer oil made only perfume inspired by Khamrah Qahwa. Warm roasted Arabic coffee, candied ginger, sweet praline, and creamy bourbon vanilla.','Gourmand Oriental','Cinnamon, Cardamom, Ginger','Roasted Coffee (Qahwa), Praline, Candied Fruits, White Flowers','Coffee Beans, Vanilla, Tonka Bean, Benzoin, Musk','Spritz 2-3 sprays on pulse points: collarbones, wrists, and behind the ears for all-day sillage.',1,1,1,0,'2026-10-01 06:43:13.763656','2026-10-01 06:43:13.763658','Lattafa Khamrah Qahwa');
INSERT INTO "products" VALUES(15,1,'Astral (FIFA)','astral-fifa','Original Manufacturer oil made only perfume inspired by Astral FIFA Edition.','Original Manufacturer oil made only perfume inspired by Astral FIFA Edition. Dynamic energizing citrus, invigorating ocean spray, and sporty woody amber.','Fresh Sporty Aquatic','Grapefruit, Marine Ozone, Mandarin','Bay Leaf, Jasmine, Lavender','Guaiac Wood, Oakmoss, Patchouli, Ambergris','Spritz 2-3 sprays on pulse points: collarbones, wrists, and behind the ears for all-day sillage.',1,0,1,0,'2026-10-01 06:43:13.765273','2026-10-01 06:43:13.765278','Astral FIFA Edition');
INSERT INTO "products" VALUES(16,1,'Aggressive','aggressive','Original Manufacturer oil made only perfume with dark woods, spice, and smoky leather.','Original Manufacturer oil made only perfume. A commanding, intensely masculine fragrance crafted with dark woods, cracked black pepper, smoky leather, and deep amber.','Intense Woody Leather','Black Pepper, Bergamot, Pink Peppercorn','Smoky Leather, Cedarwood, Vetiver','Agarwood (Oud), Dark Amber, Patchouli','Spritz 2-3 sprays on pulse points: collarbones, wrists, and behind the ears for all-day sillage.',1,1,0,0,'2026-10-01 06:43:13.767487','2026-10-01 06:43:13.767489','Aggressive');
INSERT INTO "products" VALUES(17,1,'Tom Ford Vanilla','tom-ford-vanilla','Original Manufacturer oil made only perfume inspired by Tom Ford Tobacco Vanille.','Original Manufacturer oil made only perfume inspired by Tom Ford Tobacco Vanille. Rich creamy Madagascar vanilla, aromatic spices, cocoa, and warm tonka bean.','Oriental Gourmand','Tobacco Leaf, Spicy Aromatics','Bourbon Vanilla, Cacao, Tonka Bean, Tobacco Blossom','Dried Fruits, Woody Resins','Spritz 2-3 sprays on pulse points: collarbones, wrists, and behind the ears for all-day sillage.',1,1,1,0,'2026-10-01 06:43:13.769062','2026-10-01 06:43:13.769064','Tom Ford Tobacco Vanille');
INSERT INTO "products" VALUES(18,1,'Davidoff Cool Water (Akshay Kumar)','davidoff-cool-water-akshay-kumar','Original Manufacturer oil made only perfume inspired by Davidoff Cool Water (as worn by Akshay Kumar).','Original Manufacturer oil made only perfume inspired by Davidoff Cool Water, signature fragrance of Akshay Kumar. Crisp ocean breeze, peppermint, lavender, and warm amber.','Aromatic Aquatic','Sea Water, Mint, Green Notes, Lavender, Rosemary','Sandalwood, Jasmine, Neroli, Geranium','Musk, Oakmoss, Cedar, Amber, Tobacco','Spritz 2-3 sprays on pulse points: collarbones, wrists, and behind the ears for all-day sillage.',1,1,1,0,'2026-10-01 06:43:13.770428','2026-10-01 06:43:13.770430','Davidoff Cool Water (as worn by Akshay Kumar)');
INSERT INTO "products" VALUES(19,1,'Club de Nuit Armaf','club-de-nuit-armaf','Original Manufacturer oil made only perfume inspired by Club De Nuit Intense Armaf.','Original Manufacturer oil made only perfume inspired by Club De Nuit Intense Man Armaf. Zesty lemon, smoky birch, crisp apple, blackcurrant, and ambergris.','Woody Spicy','Lemon, Pineapple, Blackcurrant, Apple, Bergamot','Birch, Jasmine, Rose','Musk, Ambergris, Patchouli, Vanilla','Spritz 2-3 sprays on pulse points: collarbones, wrists, and behind the ears for all-day sillage.',1,1,1,0,'2026-10-01 06:43:13.771752','2026-10-01 06:43:13.771753','Club De Nuit Intense Armaf');
INSERT INTO "products" VALUES(20,1,'Carolina Herrera - Good Girl','carolina-herrera-good-girl','Original Manufacturer oil made only perfume inspired by Carolina Herrera Good Girl.','Original Manufacturer oil made only perfume inspired by Carolina Herrera Good Girl. Sensual tuberose, roasted tonka bean, white sambac jasmine, and dark cocoa.','Oriental Floral','Almond, Coffee, Bergamot, Lemon','Tuberose, Jasmine Sambac, Orange Blossom, Orris','Tonka Bean, Cacao, Vanilla, Praline, Sandalwood','Spritz 2-3 sprays on pulse points: collarbones, wrists, and behind the ears for all-day sillage.',1,1,1,0,'2026-10-01 06:43:13.773084','2026-10-01 06:43:13.773086','Carolina Herrera Good Girl');
INSERT INTO "products" VALUES(21,1,'Dubai Gold','dubai-gold','Original Manufacturer oil made only perfume inspired by luxury Arabian Dubai Gold.','Original Manufacturer oil made only perfume inspired by luxury Arabian Dubai Gold. Opulent royal saffron, golden amber, damask rose, and precious Cambodian agarwood.','Oriental Amber Oud','Royal Saffron, Bergamot, Cardamom','Damask Rose, Amber, Incense','Cambodian Agarwood, White Musk, Patchouli','Spritz 2-3 sprays on pulse points: collarbones, wrists, and behind the ears for all-day sillage.',1,1,1,0,'2026-10-01 06:43:13.774417','2026-10-01 06:43:13.774419','luxury Arabian Dubai Gold');
INSERT INTO "products" VALUES(22,1,'Roja Mischief (Hardik Pandya)','roja-mischief-hardik-pandya','Original Manufacturer oil made only perfume inspired by Roja Mischief (signature scent of Hardik Pandya).','Original Manufacturer oil made only perfume inspired by Roja Mischief, worn by Hardik Pandya. Crisp bergamot, violet leaf, aromatic spice, and luxurious soft leather.','Citrus Woody Chypre','Bergamot, Lemon, Grapefruit, Lime','Lily-of-the-Valley, Rose de Mai, Jasmin de Grasse','Galbanum, Cedarwood, Pink Pepper, Benzoin, Leather','Spritz 2-3 sprays on pulse points: collarbones, wrists, and behind the ears for all-day sillage.',1,1,1,0,'2026-10-01 06:43:13.775733','2026-10-01 06:43:13.775735','Roja Mischief (signature scent of Hardik Pandya)');
INSERT INTO "products" VALUES(23,1,'Creed Silver Mountain (Shahid Kapoor/ Virat Kohli)','creed-silver-mountain-shahid-kapoor-virat-kohli','Original Manufacturer oil made only perfume inspired by Creed Silver Mountain Water (Shahid Kapoor / Virat Kohli).','Original Manufacturer oil made only perfume inspired by Creed Silver Mountain Water, signature scent of Shahid Kapoor & Virat Kohli. Sparkling green tea, blackcurrant, alpine freshness, and creamy sandalwood.','Fresh Aromatic','Bergamot, Mandarin Orange','Green Tea, Blackcurrant','Musk, Petitgrain, Sandalwood, Galbanum','Spritz 2-3 sprays on pulse points: collarbones, wrists, and behind the ears for all-day sillage.',1,1,1,0,'2026-10-01 06:43:13.777059','2026-10-01 06:43:13.777061','Creed Silver Mountain Water (Shahid Kapoor / Virat Kohli)');
INSERT INTO "products" VALUES(24,1,'Zara Unisex','zara-unisex','Original Manufacturer oil made only perfume inspired by Zara Unisex Collection.','Original Manufacturer oil made only perfume inspired by Zara Unisex Collection. Clean, versatile crisp aromatics, subtle pink pepper, and velvety cedarwood.','Fresh Woody Clean','Mandarin, Pink Pepper, Clean Cotton Accord','White Tea, Cedarwood, Lily','Amber, Vetiver, Soft White Musk','Spritz 2-3 sprays on pulse points: collarbones, wrists, and behind the ears for all-day sillage.',1,0,0,0,'2026-10-01 06:43:13.778396','2026-10-01 06:43:13.778398','Zara Unisex Collection');
INSERT INTO "products" VALUES(25,1,'Invictus','invictus','Original Manufacturer oil made only perfume inspired by Paco Rabanne Invictus.','Original Manufacturer oil made only perfume inspired by Paco Rabanne Invictus. Energizing marine accord, fresh grapefruit, aromatic bay leaf, and guaiac wood.','Woody Aquatic','Sea Notes, Grapefruit, Mandarin Orange','Bay Leaf, Jasmine','Ambergris, Guaiac Wood, Oakmoss, Patchouli','Spritz 2-3 sprays on pulse points: collarbones, wrists, and behind the ears for all-day sillage.',1,1,1,0,'2026-10-01 06:43:13.779782','2026-10-01 06:43:13.779784','Paco Rabanne Invictus');
INSERT INTO "products" VALUES(26,1,'Versace Eros','versace-eros','Original Manufacturer oil made only perfume inspired by Versace Eros.','Original Manufacturer oil made only perfume inspired by Versace Eros. Crisp Italian mint, candied green apple, tonka bean, and warm cedarwood.','Aromatic Fougere','Mint, Green Apple, Lemon','Tonka Bean, Ambroxan, Geranium','Madagascar Vanilla, Virginian Cedar, Atlas Cedar, Vetiver, Oakmoss','Spritz 2-3 sprays on pulse points: collarbones, wrists, and behind the ears for all-day sillage.',1,1,1,0,'2026-10-01 06:43:13.781214','2026-10-01 06:43:13.781216','Versace Eros');
INSERT INTO "products" VALUES(27,1,'Men in Black','men-in-black','Original Manufacturer oil made only perfume inspired by Bvlgari Man in Black.','Original Manufacturer oil made only perfume inspired by Bvlgari Man in Black. Vibrant spicy rum, magnetic leather, tuberose, and smoky guaiac wood.','Amber Floral Spicy','Spices, Rum, Tobacco','Leather, Iris, Tuberose','Tonka Bean, Guaiac Wood, Benzoin','Spritz 2-3 sprays on pulse points: collarbones, wrists, and behind the ears for all-day sillage.',1,1,1,0,'2026-10-01 06:43:13.783998','2026-10-01 06:43:13.784001','Bvlgari Man in Black');
INSERT INTO "products" VALUES(28,1,'YSL Mon Paris','ysl-mon-paris','Original Manufacturer oil made only perfume inspired by YSL Mon Paris.','Original Manufacturer oil made only perfume inspired by YSL Mon Paris. Sweet strawberry, raspberry, bergamot, white datura flower, and sensual patchouli.','Chypre Fruity','Strawberry, Raspberry, Pear, Calabrian Bergamot','Datura, Peony, Orange Blossom, Jasmine Sambac','Indonesian Patchouli Leaf, White Musk, Ambroxan, Cedar','Spritz 2-3 sprays on pulse points: collarbones, wrists, and behind the ears for all-day sillage.',1,1,1,0,'2026-10-01 06:43:13.787210','2026-10-01 06:43:13.787212','YSL Mon Paris');
INSERT INTO "products" VALUES(29,1,'Balmain Paris','balmain-paris','Original Manufacturer oil made only perfume inspired by Balmain Paris.','Original Manufacturer oil made only perfume inspired by Balmain Paris. Refined French elegance, powdery iris, velvety cedarwood, and warm sensual musk.','Woody Floral Sophisticated','Bergamot, Pink Pepper, Violet Leaves','French Iris, Damask Rose, Cedarwood','Sandalwood, Tonka Bean, White Musk','Spritz 2-3 sprays on pulse points: collarbones, wrists, and behind the ears for all-day sillage.',1,0,1,0,'2026-10-01 06:43:13.788565','2026-10-06 06:08:39.679015','Balmain Paris');
INSERT INTO "products" VALUES(30,2,'Amber Noir Luxury Car Diffuser','amber-noir-luxury-car-diffuser','Artisanal wooden car diffuser with amber, cedarwood, and rich leather notes. Lasts 60+ days.','Artisanal wooden car diffuser infused with amber, cedarwood, and leather notes. Features slow-evaporating natural beechwood cap. Keeps your car cabin effortlessly luxurious.','Woody Leather','Cardamom, Bergamot','Leather, Iris, Warm Amber','Cedarwood, Vetiver, Sandalwood','Invert bottle for 3 seconds to saturate wooden cap. Hang from rearview mirror.',1,1,1,0,'2026-10-01 06:43:13.790292','2026-10-01 06:43:13.790294','Amber Noir Luxury Car Diffuser');
INSERT INTO "products" VALUES(31,2,'Citrus Velvet Luxury Car Diffuser','citrus-velvet-luxury-car-diffuser','Artisanal hanging car diffuser with Sicilian mandarin, blue eucalyptus, and fresh mint.','Eliminates vehicle odors instantly while delivering clean, awakening aroma. Crafted with natural essential oils and slow-diffusing wooden cap.','Citrus Fresh','Sicilian Mandarin, Mint, Lemon','Blue Eucalyptus, Rosemary','Clean Musk, White Cedar','Invert bottle for 3 seconds to saturate wooden cap. Hang from rearview mirror.',1,1,1,0,'2026-10-01 06:43:13.791623','2026-10-01 06:43:13.791625','Citrus Velvet Luxury Car Diffuser');
INSERT INTO "products" VALUES(32,2,'Royal Oud & Woods Luxury Car Diffuser','royal-oud-woods-luxury-car-diffuser','Opulent Cambodian agarwood and smoky saffron designed for an executive car interior.','Bring royal nighttime grandeur into your car cabin. Rich notes of smoky agarwood, saffron, and white amber that diffuse gently without overwhelming.','Oriental Woody','Saffron, Rose, Bergamot','Agarwood (Oud), Labdanum','Amber, Sandalwood, Musk','Invert bottle for 3 seconds to saturate wooden cap. Hang from rearview mirror.',1,1,0,0,'2026-10-01 06:43:13.792960','2026-10-01 06:43:13.792962','Royal Oud & Woods Luxury Car Diffuser');
INSERT INTO "products" VALUES(33,2,'Aqua Marine Breeze Luxury Car Diffuser','aqua-marine-breeze-luxury-car-diffuser','Coastal ocean breeze, sea salt spray, and refreshing driftwood for daily commuting freshness.','Crisp, airy, and rejuvenating. Aqua Marine Breeze brings Mediterranean ocean air, sea salt, and coastal woods into your daily drive.','Aquatic Marine','Marine Ozone, Sea Salt, Lemon','Water Lily, Sage','Driftwood, Cedarwood','Invert bottle for 3 seconds to saturate wooden cap. Hang from rearview mirror.',1,0,1,0,'2026-10-01 06:43:13.794269','2026-10-01 06:43:13.794271','Aqua Marine Breeze Luxury Car Diffuser');
CREATE TABLE settings (
	id INTEGER NOT NULL, 
	"key" VARCHAR(64) NOT NULL, 
	value TEXT, 
	description VARCHAR(255), 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);
INSERT INTO "settings" VALUES(1,'company_name','Scented Bubbles','Official registered brand name','2026-09-30 14:16:37.333890','2026-09-30 14:16:37.333894');
INSERT INTO "settings" VALUES(2,'tagline','Elegance in Every Mist & Breath','Short store tagline','2026-09-30 14:16:37.335934','2026-09-30 14:16:37.335937');
INSERT INTO "settings" VALUES(3,'support_phone','7020651871','Customer support phone number','2026-09-30 14:16:37.336658','2026-10-04 10:55:55.273456');
INSERT INTO "settings" VALUES(4,'support_whatsapp','7020651871','WhatsApp contact number for click-to-chat','2026-09-30 14:16:37.337284','2026-10-04 10:54:09.618430');
INSERT INTO "settings" VALUES(5,'support_email','care@scentedbubbles.com','Customer support email','2026-09-30 14:16:37.337911','2026-09-30 14:16:37.337913');
INSERT INTO "settings" VALUES(6,'store_address','Plot 42, Fragrance Avenue, Jubilee Hills, Hyderabad - 500033','Physical store / fulfillment address','2026-09-30 14:16:37.338601','2026-09-30 14:16:37.338604');
INSERT INTO "settings" VALUES(7,'upi_id','scentedbubbles@okaxis','Store UPI VPA for customer manual payments','2026-09-30 14:16:37.339439','2026-09-30 14:16:37.339443');
INSERT INTO "settings" VALUES(8,'upi_qr_url','/static/images/placeholder_upi_qr.png','UPI QR code scan image','2026-09-30 14:16:37.340766','2026-09-30 14:16:37.340769');
INSERT INTO "settings" VALUES(9,'delivery_charge','50.00','Standard delivery fee in INR','2026-09-30 14:16:37.341576','2026-09-30 14:16:37.341579');
INSERT INTO "settings" VALUES(10,'free_delivery_threshold','999.00','Order total in INR for free shipping','2026-09-30 14:16:37.342239','2026-09-30 14:16:37.342241');
INSERT INTO "settings" VALUES(11,'cod_enabled','true','Toggle Cash on Delivery (true/false)','2026-09-30 14:16:37.342854','2026-09-30 14:16:37.342855');
INSERT INTO "settings" VALUES(12,'gst_number','36AABCS1234F1Z5','GSTIN identification','2026-09-30 14:16:37.343497','2026-09-30 14:16:37.343499');
INSERT INTO "settings" VALUES(13,'instagram_url','https://instagram.com/scentedbubbles','Instagram handle','2026-09-30 14:16:37.344109','2026-09-30 14:16:37.344111');
INSERT INTO "settings" VALUES(14,'footer_text','Handcrafted fine fragrances and artisanal car diffusers designed to refresh your world.','Footer summary','2026-09-30 14:16:37.344749','2026-09-30 14:16:37.344751');
CREATE TABLE users (
	id INTEGER NOT NULL, 
	email VARCHAR(120) NOT NULL, 
	password_hash VARCHAR(256) NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, phone VARCHAR(15), name VARCHAR(100), updated_at DATETIME, 
	PRIMARY KEY (id)
);
INSERT INTO "users" VALUES(1,'crajeev351@gmail.com','scrypt:32768:8:1$W7XG9PpVtIylJ5XW$c90ab9a8a7874395b94532a04a827bf4be562d5f0508c06da1f94aa736ab1b2afa4bcf26e6064d10ba0587c24e59e38084302c5eeaf146b395dcae9ffefc3b7b',1,'2026-10-05 04:35:34.999435','7020651871','Rajeev','2026-10-05 04:35:34.999439');
CREATE UNIQUE INDEX ix_admins_email ON admins (email);
CREATE UNIQUE INDEX ix_admins_username ON admins (username);
CREATE UNIQUE INDEX ix_users_email ON users (email);
CREATE UNIQUE INDEX ix_categories_slug ON categories (slug);
CREATE INDEX ix_categories_is_deleted ON categories (is_deleted);
CREATE INDEX ix_categories_active ON categories (active);
CREATE INDEX ix_combos_is_deleted ON combos (is_deleted);
CREATE UNIQUE INDEX ix_combos_slug ON combos (slug);
CREATE INDEX ix_combos_active ON combos (active);
CREATE INDEX ix_banners_active ON banners (active);
CREATE INDEX ix_banners_is_deleted ON banners (is_deleted);
CREATE UNIQUE INDEX ix_order_counters_date_str ON order_counters (date_str);
CREATE UNIQUE INDEX ix_settings_key ON settings ("key");
CREATE UNIQUE INDEX ix_pages_slug ON pages (slug);
CREATE INDEX ix_customers_user_id ON customers (user_id);
CREATE INDEX ix_customers_email ON customers (email);
CREATE UNIQUE INDEX ix_customers_phone ON customers (phone);
CREATE INDEX ix_products_bestseller ON products (bestseller);
CREATE INDEX ix_products_is_deleted ON products (is_deleted);
CREATE UNIQUE INDEX ix_products_slug ON products (slug);
CREATE INDEX ix_products_category_id ON products (category_id);
CREATE INDEX ix_products_active ON products (active);
CREATE INDEX ix_products_featured ON products (featured);
CREATE INDEX ix_product_variants_product_id ON product_variants (product_id);
CREATE INDEX ix_product_variants_is_deleted ON product_variants (is_deleted);
CREATE INDEX ix_product_variants_active ON product_variants (active);
CREATE UNIQUE INDEX ix_product_variants_sku ON product_variants (sku);
CREATE INDEX ix_product_images_product_id ON product_images (product_id);
CREATE UNIQUE INDEX ix_orders_order_id ON orders (order_id);
CREATE INDEX ix_orders_customer_id ON orders (customer_id);
CREATE INDEX ix_orders_payment_status ON orders (payment_status);
CREATE INDEX ix_orders_order_status ON orders (order_status);
CREATE INDEX ix_orders_created_at ON orders (created_at);
CREATE UNIQUE INDEX ix_orders_idempotency_token ON orders (idempotency_token);
CREATE INDEX ix_combo_items_product_variant_id ON combo_items (product_variant_id);
CREATE INDEX ix_combo_items_combo_id ON combo_items (combo_id);
CREATE INDEX ix_order_items_product_variant_id ON order_items (product_variant_id);
CREATE INDEX ix_order_items_order_id ON order_items (order_id);
CREATE UNIQUE INDEX ix_payments_utr ON payments (utr);
CREATE INDEX ix_payments_order_id ON payments (order_id);
CREATE INDEX ix_payments_status ON payments (status);
CREATE INDEX ix_order_status_history_created_at ON order_status_history (created_at);
CREATE INDEX ix_order_status_history_order_id ON order_status_history (order_id);
COMMIT;
