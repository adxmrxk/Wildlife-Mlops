package com.wildlife.platform.controller;

import com.wildlife.platform.model.Species;
import com.wildlife.platform.service.SpeciesService;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/species")
@RequiredArgsConstructor
public class SpeciesController {

    private final SpeciesService speciesService;

    // GET /api/species - Get all species
    @GetMapping
    public ResponseEntity<List<Species>> getAllSpecies() {
        List<Species> species = speciesService.getAllSpecies();
        return ResponseEntity.ok(species);
    }

    // GET /api/species/{id} - Get a specific species by ID
    @GetMapping("/{id}")
    public ResponseEntity<Species> getSpeciesById(@PathVariable Long id) {
        return speciesService.getSpeciesById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    // POST /api/species - Create a new species
    @PostMapping
    public ResponseEntity<Species> createSpecies(@Valid @RequestBody Species species) {
        Species savedSpecies = speciesService.saveSpecies(species);
        return ResponseEntity.status(HttpStatus.CREATED).body(savedSpecies);
    }

    // PUT /api/species/{id} - Update an existing species
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

    // DELETE /api/species/{id} - Delete a species
    @DeleteMapping("/{id}")
    public ResponseEntity<Void> deleteSpecies(@PathVariable Long id) {
        return speciesService.getSpeciesById(id)
                .map(species -> {
                    speciesService.deleteSpecies(id);
                    return ResponseEntity.noContent().<Void>build();
                })
                .orElse(ResponseEntity.notFound().build());
    }

    // GET /api/species/count - Get total species count
    @GetMapping("/count")
    public ResponseEntity<Long> getSpeciesCount() {
        long count = speciesService.countSpecies();
        return ResponseEntity.ok(count);
    }
}
