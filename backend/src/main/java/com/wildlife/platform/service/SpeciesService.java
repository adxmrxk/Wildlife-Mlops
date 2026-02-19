package com.wildlife.platform.service;

import com.wildlife.platform.model.Species;
import com.wildlife.platform.repository.SpeciesRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;

@Service
@RequiredArgsConstructor
public class SpeciesService {

    private final SpeciesRepository speciesRepository;

    // Get all species
    public List<Species> getAllSpecies() {
        return speciesRepository.findAll();
    }

    // Get a specific species by ID
    public Optional<Species> getSpeciesById(Long id) {
        return speciesRepository.findById(id);
    }

    // Get a species by its scientific name
    public Optional<Species> getSpeciesByName(String name) {
        return speciesRepository.findByName(name);
    }

    // Create or update a species
    @Transactional
    public Species saveSpecies(Species species) {
        return speciesRepository.save(species);
    }

    // Delete a species
    @Transactional
    public void deleteSpecies(Long id) {
        speciesRepository.deleteById(id);
    }

    // Count total species
    public long countSpecies() {
        return speciesRepository.count();
    }
}
