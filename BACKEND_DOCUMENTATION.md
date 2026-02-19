# Wildlife MLOps Platform - Backend Development Guide

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [Project Structure](#project-structure)
5. [Core Concepts](#core-concepts)
6. [Data Models](#data-models)
7. [Repositories](#repositories)
8. [Services](#services)
9. [Controllers (REST API)](#controllers-rest-api)
10. [Database Configuration](#database-configuration)
11. [Request Flow](#request-flow)
12. [Testing](#testing)
13. [Running the Application](#running-the-application)
14. [API Endpoints](#api-endpoints)
15. [Key Learnings](#key-learnings)

---

## Overview

The Wildlife MLOps Platform backend is a **Spring Boot 3.2.3** application built with **Java 17**. It provides a REST API for managing wildlife species and classification predictions. The backend follows a layered architecture pattern with clear separation of concerns.

### Purpose
- Manage wildlife species database
- Store and retrieve ML prediction results
- Provide REST API for frontend and ML services
- Handle business logic and validation

---

## Architecture

### Layered Architecture (3 Layers)

```
┌─────────────────────────────────────────────────┐
│  CLIENT LAYER (Frontend / External APIs)       │
│  - React Frontend (Port 5173)                  │
│  - ML Service (Port 8000)                      │
└────────────────────┬────────────────────────────┘
                     │ HTTP/JSON
                     ↓
┌─────────────────────────────────────────────────┐
│  PRESENTATION LAYER (Controllers)               │
│  - HealthController                             │
│  - SpeciesController                            │
│  - PredictionController                         │
│                                                 │
│  Responsibilities:                              │
│  ✓ Handle HTTP requests/responses              │
│  ✓ Validate input (basic)                      │
│  ✓ Convert JSON ↔ Java objects                 │
│  ✓ Return appropriate HTTP status codes        │
└────────────────────┬────────────────────────────┘
                     │ Method Calls
                     ↓
┌─────────────────────────────────────────────────┐
│  BUSINESS LOGIC LAYER (Services)                │
│  - SpeciesService                               │
│  - PredictionService                            │
│                                                 │
│  Responsibilities:                              │
│  ✓ Business rules and validation               │
│  ✓ Transaction management                      │
│  ✓ Complex operations                          │
│  ✓ Orchestrate multiple repositories           │
└────────────────────┬────────────────────────────┘
                     │ Repository Interface
                     ↓
┌─────────────────────────────────────────────────┐
│  DATA ACCESS LAYER (Repositories)               │
│  - SpeciesRepository                            │
│  - PredictionRepository                         │
│                                                 │
│  Responsibilities:                              │
│  ✓ Database CRUD operations                    │
│  ✓ Custom queries                               │
│  ✓ No business logic!                          │
└────────────────────┬────────────────────────────┘
                     │ JPA/Hibernate (ORM)
                     ↓
┌─────────────────────────────────────────────────┐
│  DATABASE                                       │
│  - PostgreSQL (Production)                      │
│  - H2 (Development/Testing)                     │
│                                                 │
│  Tables: species, predictions                   │
└─────────────────────────────────────────────────┘
```

### Why Layered Architecture?

1. **Separation of Concerns**: Each layer has a single, well-defined responsibility
2. **Testability**: Each layer can be tested independently
3. **Maintainability**: Changes in one layer don't affect others
4. **Reusability**: Services can be called by multiple controllers
5. **Scalability**: Easy to add new features or modify existing ones

---

## Technology Stack

### Core Framework
- **Spring Boot 3.2.3** - Application framework
- **Java 17** - Programming language
- **Maven 3.9.11** - Dependency management and build tool

### Spring Boot Starters
- **spring-boot-starter-web** - RESTful web services, embedded Tomcat
- **spring-boot-starter-data-jpa** - JPA and Hibernate for database operations
- **spring-boot-starter-validation** - Bean validation (JSR-380)
- **spring-boot-starter-actuator** - Health checks and metrics
- **spring-boot-devtools** - Hot reload for development

### Database
- **PostgreSQL** - Production database (JDBC driver included)
- **H2 Database** - In-memory database for development and testing
- **Hibernate** - ORM (Object-Relational Mapping)

### Utilities
- **Lombok** - Reduces boilerplate code (@Data, @Builder, etc.)
- **JUnit 5** - Testing framework

---

## Project Structure

```
backend/
├── pom.xml                                    # Maven configuration
├── mvnw, mvnw.cmd                            # Maven wrapper scripts
├── src/
│   ├── main/
│   │   ├── java/com/wildlife/platform/
│   │   │   ├── WildlifeApplication.java      # Main entry point
│   │   │   ├── config/
│   │   │   │   └── CorsConfig.java           # CORS configuration
│   │   │   ├── controller/
│   │   │   │   ├── HealthController.java     # Health check endpoint
│   │   │   │   ├── SpeciesController.java    # Species REST API
│   │   │   │   └── PredictionController.java # Predictions REST API
│   │   │   ├── model/
│   │   │   │   ├── Species.java              # Species entity
│   │   │   │   └── Prediction.java           # Prediction entity
│   │   │   ├── repository/
│   │   │   │   ├── SpeciesRepository.java    # Species data access
│   │   │   │   └── PredictionRepository.java # Prediction data access
│   │   │   └── service/
│   │   │       ├── SpeciesService.java       # Species business logic
│   │   │       └── PredictionService.java    # Prediction business logic
│   │   └── resources/
│   │       ├── application.properties         # Main configuration
│   │       └── application-dev.properties     # Dev profile (H2)
│   └── test/
│       ├── java/com/wildlife/platform/
│       │   └── WildlifeApplicationTests.java  # Integration tests
│       └── resources/
│           └── application-test.properties    # Test configuration
└── target/                                    # Compiled output (generated)
```

---

## Core Concepts

### 1. Dependency Injection

Spring automatically creates and connects objects (beans).

```java
@Service
@RequiredArgsConstructor  // Lombok generates constructor
public class SpeciesService {
    // Spring automatically injects this!
    private final SpeciesRepository speciesRepository;
}
```

**Without Dependency Injection:**
```java
public class SpeciesService {
    private SpeciesRepository repo = new SpeciesRepository(); // ❌ Tight coupling
}
```

**With Dependency Injection:**
- Spring creates SpeciesRepository
- Spring creates SpeciesService
- Spring injects repository into service
- Loose coupling, easy to test, easy to swap implementations

### 2. Annotations

Annotations provide metadata to Spring:

| Annotation | Purpose | Where Used |
|------------|---------|------------|
| `@SpringBootApplication` | Main entry point | WildlifeApplication.java |
| `@RestController` | REST API controller | Controllers |
| `@Service` | Business logic service | Services |
| `@Repository` | Data access layer | Repositories |
| `@Entity` | Database table | Models |
| `@Transactional` | Database transaction | Service methods |
| `@Autowired` | Inject dependency | Anywhere (Lombok does this) |
| `@GetMapping`, `@PostMapping`, etc. | HTTP endpoints | Controller methods |

### 3. JPA (Java Persistence API)

**ORM (Object-Relational Mapping)**: Bridges Java objects and database tables

```java
@Entity                          // This is a database table
@Table(name = "species")
public class Species {
    @Id                          // Primary key
    @GeneratedValue              // Auto-increment
    private Long id;

    @Column(unique = true)       // Database column
    private String name;
}
```

**Hibernate** (JPA implementation) automatically:
- Creates tables from entities
- Generates SQL queries
- Converts rows ↔ objects
- Manages relationships

### 4. Spring Data JPA Repositories

**No implementation needed!** Just define the interface:

```java
public interface SpeciesRepository extends JpaRepository<Species, Long> {
    // Spring generates implementation automatically!
}
```

**Free methods you get:**
- `save(entity)` - Insert or update
- `findById(id)` - Find by primary key
- `findAll()` - Get all records
- `deleteById(id)` - Delete by ID
- `count()` - Count records
- And many more!

**Custom queries by method name:**
```java
Optional<Species> findByName(String name);
// Spring generates: SELECT * FROM species WHERE name = ?

List<Species> findByActiveTrue();
// Spring generates: SELECT * FROM species WHERE active = true

List<Species> findByCommonNameContaining(String keyword);
// Spring generates: SELECT * FROM species WHERE common_name LIKE %keyword%
```

### 5. REST API Design

**RESTful principles:**
- Use HTTP methods correctly (GET, POST, PUT, DELETE)
- Resource-based URLs (`/api/species`, not `/api/getSpecies`)
- Proper HTTP status codes (200, 201, 404, 500, etc.)
- Stateless (no server-side sessions for API)

---

## Data Models

### Species Entity

Represents a wildlife species in the database.

```java
@Entity
@Table(name = "species")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Species {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @NotBlank(message = "Species name is required")
    @Column(unique = true, nullable = false)
    private String name;

    @Column(name = "common_name")
    private String commonName;

    @Column(length = 1000)
    private String description;

    @Column(nullable = false)
    @Builder.Default
    private Boolean active = true;
}
```

**Annotations Explained:**
- `@Entity` - Marks this as a JPA entity (database table)
- `@Table(name = "species")` - Table name in database
- `@Data` - Lombok: generates getters, setters, toString, equals, hashCode
- `@Builder` - Lombok: enables builder pattern
- `@NoArgsConstructor` - Lombok: generates no-args constructor
- `@AllArgsConstructor` - Lombok: generates all-args constructor
- `@Id` - Primary key field
- `@GeneratedValue` - Auto-increment ID
- `@NotBlank` - Validation: cannot be null or empty
- `@Column` - Column configuration (unique, nullable, length, name)
- `@Builder.Default` - Use default value in builder pattern

**Database Table (auto-generated):**
```sql
CREATE TABLE species (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(255) UNIQUE NOT NULL,
    common_name VARCHAR(255),
    description VARCHAR(1000),
    active BOOLEAN NOT NULL DEFAULT TRUE
);
```

**Using the Builder Pattern:**
```java
Species lion = Species.builder()
    .name("Panthera leo")
    .commonName("African Lion")
    .description("Large cat native to Africa")
    .active(true)  // or omit - defaults to true
    .build();
```

### Prediction Entity

Represents an ML prediction result.

```java
@Entity
@Table(name = "predictions")
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class Prediction {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "image_name", nullable = false)
    private String imageName;

    @Column(name = "image_url")
    private String imageUrl;

    @ManyToOne(fetch = FetchType.EAGER)
    @JoinColumn(name = "species_id", nullable = false)
    private Species predictedSpecies;

    @DecimalMin(value = "0.0", message = "Confidence must be between 0 and 1")
    @DecimalMax(value = "1.0", message = "Confidence must be between 0 and 1")
    @Column(nullable = false)
    private Double confidence;

    @Column(name = "model_version")
    private String modelVersion;

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @PrePersist
    protected void onCreate() {
        createdAt = LocalDateTime.now();
    }
}
```

**New Annotations:**
- `@ManyToOne` - Relationship: Many predictions → One species
- `@JoinColumn` - Foreign key column name
- `@DecimalMin`, `@DecimalMax` - Validation for numeric ranges
- `@PrePersist` - Lifecycle callback: runs before saving to database

**Relationship Explained:**

```
Species (One)                  Prediction (Many)
┌──────────┐                  ┌──────────────┐
│ id = 1   │ ←───────────────│ species_id=1 │
│ Lion     │                  │ lion_1.jpg   │
└──────────┘                  ├──────────────┤
                              │ species_id=1 │
                              │ lion_2.jpg   │
                              ├──────────────┤
                              │ species_id=1 │
                              │ lion_3.jpg   │
                              └──────────────┘
```

**Database Tables:**
```sql
CREATE TABLE predictions (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    image_name VARCHAR(255) NOT NULL,
    image_url VARCHAR(255),
    species_id BIGINT NOT NULL,
    confidence DOUBLE NOT NULL,
    model_version VARCHAR(255),
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY (species_id) REFERENCES species(id)
);
```

---

## Repositories

Repositories provide data access without writing SQL.

### SpeciesRepository

```java
@Repository
public interface SpeciesRepository extends JpaRepository<Species, Long> {
    Optional<Species> findByName(String name);
}
```

**Inherited Methods (from JpaRepository):**
```java
// Create/Update
Species save(Species species);
List<Species> saveAll(Iterable<Species> species);

// Read
Optional<Species> findById(Long id);
List<Species> findAll();
List<Species> findAllById(Iterable<Long> ids);
boolean existsById(Long id);
long count();

// Delete
void deleteById(Long id);
void delete(Species species);
void deleteAll();
```

**Custom Query Method:**
```java
Optional<Species> findByName(String name);
```
Spring translates this to: `SELECT * FROM species WHERE name = ?`

### PredictionRepository

```java
@Repository
public interface PredictionRepository extends JpaRepository<Prediction, Long> {
    List<Prediction> findByPredictedSpeciesId(Long speciesId);
    List<Prediction> findByModelVersion(String modelVersion);
}
```

**Custom Queries Explained:**

```java
// Find all predictions for a specific species
List<Prediction> findByPredictedSpeciesId(Long speciesId);
// SQL: SELECT * FROM predictions WHERE species_id = ?

// Find all predictions from a specific model
List<Prediction> findByModelVersion(String modelVersion);
// SQL: SELECT * FROM predictions WHERE model_version = ?
```

---

## Services

Services contain business logic and orchestrate repositories.

### SpeciesService

```java
@Service
@RequiredArgsConstructor
public class SpeciesService {

    private final SpeciesRepository speciesRepository;

    public List<Species> getAllSpecies() {
        return speciesRepository.findAll();
    }

    public Optional<Species> getSpeciesById(Long id) {
        return speciesRepository.findById(id);
    }

    public Optional<Species> getSpeciesByName(String name) {
        return speciesRepository.findByName(name);
    }

    @Transactional
    public Species saveSpecies(Species species) {
        // Business logic goes here:
        // - Additional validation
        // - Check for duplicates
        // - Send notifications
        // - Update caches
        return speciesRepository.save(species);
    }

    @Transactional
    public void deleteSpecies(Long id) {
        speciesRepository.deleteById(id);
    }

    public long countSpecies() {
        return speciesRepository.count();
    }
}
```

**Key Concepts:**

**`@Service`**: Marks this as a Spring service bean

**`@RequiredArgsConstructor`**: Lombok generates constructor for `final` fields
```java
// Generated by Lombok:
public SpeciesService(SpeciesRepository speciesRepository) {
    this.speciesRepository = speciesRepository;
}
```

**`@Transactional`**: Database transaction wrapper
- All operations succeed, or all rollback
- Ensures data consistency
- Example: If saving fails, nothing is committed

**`Optional<T>`**: Type-safe way to handle null values
```java
Optional<Species> species = getSpeciesById(999);

// Good way:
if (species.isPresent()) {
    Species s = species.get();
    // use s
}

// Or:
species.ifPresent(s -> System.out.println(s.getName()));

// Or:
String name = species.map(Species::getName).orElse("Unknown");
```

### PredictionService

```java
@Service
@RequiredArgsConstructor
public class PredictionService {

    private final PredictionRepository predictionRepository;

    public List<Prediction> getAllPredictions() {
        return predictionRepository.findAll();
    }

    public Optional<Prediction> getPredictionById(Long id) {
        return predictionRepository.findById(id);
    }

    public List<Prediction> getPredictionsBySpecies(Long speciesId) {
        return predictionRepository.findByPredictedSpeciesId(speciesId);
    }

    public List<Prediction> getPredictionsByModelVersion(String modelVersion) {
        return predictionRepository.findByModelVersion(modelVersion);
    }

    @Transactional
    public Prediction savePrediction(Prediction prediction) {
        return predictionRepository.save(prediction);
    }

    @Transactional
    public void deletePrediction(Long id) {
        predictionRepository.deleteById(id);
    }

    public long countPredictions() {
        return predictionRepository.count();
    }

    // Business logic example:
    public Double getAverageConfidence() {
        List<Prediction> predictions = predictionRepository.findAll();
        if (predictions.isEmpty()) {
            return 0.0;
        }
        return predictions.stream()
                .mapToDouble(Prediction::getConfidence)
                .average()
                .orElse(0.0);
    }
}
```

**Java Streams Example:**
```java
predictions.stream()              // Convert list to stream
    .mapToDouble(Prediction::getConfidence)  // Extract confidence
    .average()                    // Calculate average
    .orElse(0.0);                // Default if empty
```

---

## Controllers (REST API)

Controllers handle HTTP requests and return responses.

### HTTP Methods (CRUD)

| HTTP Method | Purpose | Example |
|------------|---------|---------|
| GET | Read data | Get all species |
| POST | Create data | Create new species |
| PUT | Update data | Update existing species |
| DELETE | Delete data | Delete species |
| PATCH | Partial update | Update only name |

### HTTP Status Codes

| Code | Meaning | When to use |
|------|---------|------------|
| 200 OK | Success | Successful GET, PUT |
| 201 Created | Resource created | Successful POST |
| 204 No Content | Success, no data | Successful DELETE |
| 400 Bad Request | Invalid input | Validation error |
| 404 Not Found | Resource not found | ID doesn't exist |
| 500 Internal Server Error | Server error | Unexpected exception |

### SpeciesController

```java
@RestController
@RequestMapping("/api/species")
@RequiredArgsConstructor
public class SpeciesController {

    private final SpeciesService speciesService;

    @GetMapping
    public ResponseEntity<List<Species>> getAllSpecies() {
        List<Species> species = speciesService.getAllSpecies();
        return ResponseEntity.ok(species);
    }

    @GetMapping("/{id}")
    public ResponseEntity<Species> getSpeciesById(@PathVariable Long id) {
        return speciesService.getSpeciesById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    public ResponseEntity<Species> createSpecies(@Valid @RequestBody Species species) {
        Species savedSpecies = speciesService.saveSpecies(species);
        return ResponseEntity.status(HttpStatus.CREATED).body(savedSpecies);
    }

    @PutMapping("/{id}")
    public ResponseEntity<Species> updateSpecies(
            @PathVariable Long id,
            @Valid @RequestBody Species species) {
        return speciesService.getSpeciesById(id)
                .map(existingSpecies -> {
                    species.setId(id);
                    Species updatedSpecies = speciesService.saveSpecies(species);
                    return ResponseEntity.ok(updatedSpecies);
                })
                .orElse(ResponseEntity.notFound().build());
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteSpecies(@PathVariable Long id) {
        return speciesService.getSpeciesById(id)
                .map(species -> {
                    speciesService.deleteSpecies(id);
                    return ResponseEntity.noContent().<Void>build();
                })
                .orElse(ResponseEntity.notFound().build());
    }

    @GetMapping("/count")
    public ResponseEntity<Long> getSpeciesCount() {
        long count = speciesService.countSpecies();
        return ResponseEntity.ok(count);
    }
}
```

**Annotations:**
- `@RestController` - Combines `@Controller` + `@ResponseBody`
- `@RequestMapping("/api/species")` - Base path for all endpoints
- `@GetMapping`, `@PostMapping`, etc. - HTTP method mapping
- `@PathVariable` - Extract value from URL path
- `@RequestBody` - Extract JSON from request body
- `@Valid` - Validate input using Bean Validation

**Example Requests:**

```bash
# GET all species
curl http://localhost:8080/api/species

# GET one species
curl http://localhost:8080/api/species/1

# POST create species
curl -X POST http://localhost:8080/api/species \
  -H "Content-Type: application/json" \
  -d '{"name":"Panthera leo","commonName":"Lion"}'

# PUT update species
curl -X PUT http://localhost:8080/api/species/1 \
  -H "Content-Type: application/json" \
  -d '{"name":"Panthera leo","commonName":"African Lion"}'

# DELETE species
curl -X DELETE http://localhost:8080/api/species/1

# GET count
curl http://localhost:8080/api/species/count
```

---

## Database Configuration

### Profiles

Spring profiles allow different configurations for different environments.

**application.properties** (Main config):
```properties
spring.application.name=wildlife-platform
server.port=8080

# Active Profile
spring.profiles.active=dev

# PostgreSQL (Production)
spring.datasource.url=jdbc:postgresql://localhost:5432/wildlife_db
spring.datasource.username=wildlife_user
spring.datasource.password=wildlife_pass
spring.datasource.driver-class-name=org.postgresql.Driver

# JPA/Hibernate
spring.jpa.hibernate.ddl-auto=update
spring.jpa.show-sql=true
spring.jpa.properties.hibernate.dialect=org.hibernate.dialect.PostgreSQLDialect
spring.jpa.properties.hibernate.format_sql=true

# Actuator
management.endpoints.web.exposure.include=health,info,metrics
```

**application-dev.properties** (Development):
```properties
# H2 In-Memory Database
spring.datasource.url=jdbc:h2:mem:wildlife_dev
spring.datasource.driver-class-name=org.h2.Driver
spring.datasource.username=sa
spring.datasource.password=

# JPA Configuration
spring.jpa.hibernate.ddl-auto=create-drop
spring.jpa.show-sql=true
spring.jpa.properties.hibernate.dialect=org.hibernate.dialect.H2Dialect

# H2 Console
spring.h2.console.enabled=true
```

**application-test.properties** (Testing):
```properties
# H2 In-Memory Database
spring.datasource.url=jdbc:h2:mem:testdb
spring.datasource.driver-class-name=org.h2.Driver
spring.datasource.username=sa
spring.datasource.password=

# JPA Configuration
spring.jpa.hibernate.ddl-auto=create-drop
spring.jpa.show-sql=true
spring.jpa.properties.hibernate.dialect=org.hibernate.dialect.H2Dialect

# H2 Console
spring.h2.console.enabled=true
```

### Hibernate DDL Auto Modes

| Mode | Description | When to use |
|------|-------------|------------|
| `create` | Drop and recreate tables on startup | Never in production! |
| `create-drop` | Create on startup, drop on shutdown | Testing |
| `update` | Update schema if needed | Development |
| `validate` | Validate schema matches entities | Production |
| `none` | Do nothing | Production with migration tools |

---

## Request Flow

Let's trace a complete request from frontend to database and back.

### Example: Creating a Species

**1. Frontend (React) sends HTTP POST:**
```javascript
fetch('http://localhost:8080/api/species', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: "Panthera leo",
    commonName: "African Lion",
    description: "Large cat native to Africa"
  })
})
```

**2. Spring receives request:**
- Embedded Tomcat (web server) receives HTTP request
- Spring DispatcherServlet routes to correct controller
- Matches URL `/api/species` + POST method
- Finds `SpeciesController.createSpecies()`

**3. Controller converts JSON to object:**
```java
@PostMapping
public ResponseEntity<Species> createSpecies(@Valid @RequestBody Species species) {
    // Jackson (JSON library) converts:
    // {"name":"Panthera leo",...} → Species object

    // @Valid triggers validation
    // @NotBlank on name field

    Species savedSpecies = speciesService.saveSpecies(species);
    return ResponseEntity.status(HttpStatus.CREATED).body(savedSpecies);
}
```

**4. Service processes request:**
```java
@Transactional
public Species saveSpecies(Species species) {
    // Start database transaction

    // Business logic can go here:
    // - Check for duplicates
    // - Validate rules
    // - Send notifications

    return speciesRepository.save(species);

    // Commit transaction
}
```

**5. Repository saves to database:**
```java
public interface SpeciesRepository extends JpaRepository<Species, Long> {
    // save() is inherited from JpaRepository
}

// Hibernate generates SQL:
// INSERT INTO species (name, common_name, description, active)
// VALUES ('Panthera leo', 'African Lion', 'Large cat...', true);
```

**6. Database returns generated ID:**
```sql
-- Database auto-increments ID
-- Returns: id = 1
```

**7. Object flows back up:**
```
Database → Hibernate (adds ID to object)
         → Repository
         → Service
         → Controller
```

**8. Controller converts to JSON:**
```java
return ResponseEntity.status(HttpStatus.CREATED).body(savedSpecies);

// Jackson converts Species object → JSON:
// {
//   "id": 1,
//   "name": "Panthera leo",
//   "commonName": "African Lion",
//   "description": "Large cat native to Africa",
//   "active": true
// }

// HTTP Response:
// Status: 201 Created
// Content-Type: application/json
// Body: {...}
```

**9. Frontend receives response:**
```javascript
.then(response => response.json())
.then(species => {
  console.log('Created species:', species);
  // { id: 1, name: "Panthera leo", ... }
})
```

---

## Testing

### Spring Boot Test

```java
@SpringBootTest
@ActiveProfiles("test")
class WildlifeApplicationTests {

    @Test
    void contextLoads() {
        // This test verifies that the Spring application context loads successfully
        // It checks:
        // ✓ All beans can be created
        // ✓ Dependencies are wired correctly
        // ✓ Configuration is valid
        // ✓ Database connection works
    }
}
```

**`@SpringBootTest`**: Loads full Spring application context

**`@ActiveProfiles("test")`**: Uses application-test.properties

### Running Tests

```bash
cd backend
./mvnw test
```

**What happens:**
1. Maven compiles code
2. Spring Boot starts with test profile
3. H2 in-memory database is created
4. Tables are created from entities
5. Tests run
6. Database is dropped
7. Spring Boot shuts down

---

## Running the Application

### Development Mode (H2 Database)

```bash
cd backend
./mvnw spring-boot:run
```

**What happens:**
1. Maven downloads dependencies (first time only)
2. Compiles Java code
3. Spring Boot starts
4. Reads `application.properties` (sees `spring.profiles.active=dev`)
5. Loads `application-dev.properties`
6. Connects to H2 in-memory database
7. Hibernate creates tables from entities
8. Embedded Tomcat starts on port 8080
9. Application is ready!

**Access:**
- API: http://localhost:8080/api/species
- Health: http://localhost:8080/api/health
- Actuator: http://localhost:8080/actuator
- H2 Console: http://localhost:8080/h2-console
  - JDBC URL: `jdbc:h2:mem:wildlife_dev`
  - Username: `sa`
  - Password: (empty)

### Production Mode (PostgreSQL)

**1. Start PostgreSQL:**
```bash
docker run --name wildlife-postgres \
  -e POSTGRES_DB=wildlife_db \
  -e POSTGRES_USER=wildlife_user \
  -e POSTGRES_PASSWORD=wildlife_pass \
  -p 5432:5432 \
  -d postgres:15
```

**2. Update configuration:**
```properties
# application.properties
spring.profiles.active=prod  # Remove this or change to prod
```

**3. Run application:**
```bash
./mvnw spring-boot:run
```

---

## API Endpoints

### Health Check

```bash
GET http://localhost:8080/api/health
```

**Response:**
```json
{
  "status": "UP"
}
```

### Species Endpoints

**Get all species:**
```bash
GET /api/species
```

**Get species by ID:**
```bash
GET /api/species/{id}
```

**Create species:**
```bash
POST /api/species
Content-Type: application/json

{
  "name": "Panthera leo",
  "commonName": "African Lion",
  "description": "Large cat native to Africa"
}
```

**Update species:**
```bash
PUT /api/species/{id}
Content-Type: application/json

{
  "name": "Panthera leo",
  "commonName": "Lion",
  "description": "Updated description"
}
```

**Delete species:**
```bash
DELETE /api/species/{id}
```

**Count species:**
```bash
GET /api/species/count
```

### Prediction Endpoints

**Get all predictions:**
```bash
GET /api/predictions
```

**Get prediction by ID:**
```bash
GET /api/predictions/{id}
```

**Get predictions by species:**
```bash
GET /api/predictions/species/{speciesId}
```

**Get predictions by model version:**
```bash
GET /api/predictions/model/{version}
```

**Create prediction:**
```bash
POST /api/predictions
Content-Type: application/json

{
  "imageName": "lion_image.jpg",
  "imageUrl": "https://s3.amazonaws.com/...",
  "predictedSpecies": {
    "id": 1
  },
  "confidence": 0.95,
  "modelVersion": "v1.0.0"
}
```

**Delete prediction:**
```bash
DELETE /api/predictions/{id}
```

**Get statistics:**
```bash
GET /api/predictions/stats
```

**Response:**
```json
{
  "total": 150,
  "averageConfidence": 0.87
}
```

---

## Key Learnings

### 1. Spring Boot Fundamentals
- **Auto-configuration**: Spring Boot configures most things automatically
- **Starter dependencies**: Bundles of related dependencies
- **Embedded server**: No need for external Tomcat/Jetty
- **Opinionated defaults**: Convention over configuration

### 2. Layered Architecture Benefits
- **Separation of concerns**: Each layer has one responsibility
- **Testability**: Test each layer independently
- **Maintainability**: Easy to modify and extend
- **Reusability**: Services can be used by multiple controllers

### 3. JPA and Hibernate
- **ORM eliminates SQL**: Work with Java objects, not SQL
- **Automatic schema generation**: Tables created from entities
- **Relationship mapping**: `@ManyToOne`, `@OneToMany`, etc.
- **Query generation**: Method names become SQL queries

### 4. Dependency Injection
- **Loose coupling**: Classes don't create their dependencies
- **Testability**: Easy to mock dependencies
- **Flexibility**: Swap implementations easily
- **Lifecycle management**: Spring manages object creation/destruction

### 5. RESTful API Design
- **Resource-based URLs**: `/api/species`, not `/api/getSpecies`
- **HTTP methods**: Use GET, POST, PUT, DELETE correctly
- **Status codes**: Return appropriate codes (200, 201, 404, etc.)
- **JSON**: Standard data format for APIs

### 6. Configuration Profiles
- **Environment-specific config**: Dev, test, prod
- **Property files**: Externalize configuration
- **Override mechanism**: Profiles override base properties

### 7. Validation
- **Bean Validation**: Use `@NotBlank`, `@DecimalMin`, etc.
- **`@Valid` annotation**: Trigger validation in controllers
- **Automatic error responses**: Spring returns 400 for validation errors

### 8. Transaction Management
- **`@Transactional`**: Ensures data consistency
- **Rollback**: Failed operations don't corrupt data
- **ACID properties**: Atomicity, Consistency, Isolation, Durability

### 9. Exception Handling
- **Optional<T>**: Avoid null pointer exceptions
- **ResponseEntity**: Control HTTP responses
- **Global exception handlers**: Centralize error handling (not implemented yet)

### 10. Development Best Practices
- **H2 for development**: Fast, no setup required
- **PostgreSQL for production**: Robust, feature-rich
- **Lombok**: Reduces boilerplate code
- **DevTools**: Hot reload for faster development

---

## Next Steps

After mastering the backend, the next topics to learn are:

1. **Machine Learning Pipeline**
   - PyTorch and transfer learning
   - FastAPI inference service
   - Model training and deployment

2. **Docker and Containers**
   - Containerize applications
   - Docker Compose orchestration

3. **Message Queues (Kafka)**
   - Event-driven architecture
   - Asynchronous processing

4. **Caching (Redis)**
   - Performance optimization
   - Session management

5. **CI/CD (Jenkins)**
   - Automated testing and deployment
   - Build pipelines

6. **Infrastructure as Code (Terraform)**
   - Cloud resource provisioning
   - AWS infrastructure

7. **Kubernetes and Helm**
   - Container orchestration
   - Scalability and high availability

8. **Monitoring (Prometheus/Grafana)**
   - Metrics and dashboards
   - Alerting

---

## Glossary

**API (Application Programming Interface)**: Interface for programs to communicate

**Bean**: Object managed by Spring framework

**Controller**: Handles HTTP requests and responses

**CRUD**: Create, Read, Update, Delete operations

**DTO (Data Transfer Object)**: Object for transferring data between layers

**Entity**: Java class mapped to database table

**HTTP**: Hypertext Transfer Protocol

**JPA**: Java Persistence API (ORM standard)

**JSON**: JavaScript Object Notation (data format)

**Lombok**: Library to reduce boilerplate code

**Maven**: Build tool and dependency manager

**ORM**: Object-Relational Mapping

**Repository**: Interface for database operations

**REST**: Representational State Transfer (API design)

**Service**: Business logic layer

**Spring Boot**: Framework for building Java applications

**Transaction**: All-or-nothing database operation

---

**Created:** February 16, 2026
**Author:** Wildlife MLOps Platform Development Team
**Version:** 1.0
