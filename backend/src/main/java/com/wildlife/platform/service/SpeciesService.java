package com.wildlife.platform.service;

import com.wildlife.platform.model.Species;
import com.wildlife.platform.repository.SpeciesRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.cache.annotation.CacheEvict;
import org.springframework.cache.annotation.Cacheable;
import org.springframework.cache.annotation.Caching;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.Optional;

@Service
@RequiredArgsConstructor
public class SpeciesService {

    private final SpeciesRepository speciesRepository;

    // Get all species — cached, invalidated when any species is saved/deleted
    @Cacheable("species")
    public List<Species> getAllSpecies() {
        return speciesRepository.findAll();
    }

    // Get a specific species by ID — cached per ID
    @Cacheable(value = "speciesById", key = "#id")
    public Optional<Species> getSpeciesById(Long id) {
        return speciesRepository.findById(id);
    }

    // Get a species by its scientific name — cached per name (used on every prediction)
    @Cacheable(value = "speciesByName", key = "#name")
    public Optional<Species> getSpeciesByName(String name) {
        return speciesRepository.findByName(name);
    }

    // Create or update a species — evict all species caches so next read is fresh
    @Transactional
    @Caching(evict = {
            @CacheEvict("species"),
            @CacheEvict(value = "speciesById", key = "#result.id", condition = "#result != null"),
            @CacheEvict(value = "speciesByName", key = "#result.name", condition = "#result != null")
    })
    public Species saveSpecies(Species species) {
        return speciesRepository.save(species);
    }

    // Delete a species — evict all species caches
    @Transactional
    @Caching(evict = {
            @CacheEvict("species"),
            @CacheEvict(value = "speciesById", key = "#id"),
            @CacheEvict(value = "speciesByName", allEntries = true)
    })
    public void deleteSpecies(Long id) {
        speciesRepository.deleteById(id);
    }

    // Count total species
    public long countSpecies() {
        return speciesRepository.count();
    }
}
